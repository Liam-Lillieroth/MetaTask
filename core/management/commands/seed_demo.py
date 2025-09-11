"""
Seed demo data: organizations, users, profiles, teams, workflows, steps, transitions,
and work items. Idempotent, safe to run multiple times.
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from core.models import Organization, UserProfile as OrgUserProfile, Team, JobType


class Command(BaseCommand):
    help = "Seed demo orgs, users, teams, workflows, and work items"

    def add_arguments(self, parser):
        parser.add_argument("--password", default="DemoPass123!", help="Password for created users")
        parser.add_argument("--orgs", nargs="*", help="Optional list of org slugs to seed (default: demo-corp qa-sandbox)")

    @transaction.atomic
    def handle(self, *args, **opts):
        password = opts["password"]
        org_slugs = opts["orgs"] or ["demo-corp", "qa-sandbox"]

        # 1) Ensure organizations
        org_specs = {
            "demo-corp": {"name": "Demo Corp", "type": "business"},
            "qa-sandbox": {"name": "QA Sandbox", "type": "business"},
        }

        orgs = []
        for slug in org_slugs:
            spec = org_specs.get(slug) or {"name": slug.replace("-", " ").title(), "type": "business"}
            org, _ = Organization.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": spec["name"],
                    "organization_type": spec["type"],
                    "is_active": True,
                },
            )
            orgs.append(org)
            self.stdout.write(self.style.SUCCESS(f"✓ Org ready: {org.name} ({org.slug})"))

        # 2) Create users and org profiles per org
        User = get_user_model()
        def ensure_user(username, email, first_name, last_name, password):
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"email": email, "first_name": first_name, "last_name": last_name},
            )
            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(f"  ↳ user created: {username}")
            else:
                self.stdout.write(f"  ↳ user exists: {username}")
            return user

        profiles_by_org = {}
        for org in orgs:
            if org.slug == "demo-corp":
                users_spec = [
                    ("demoadmin", "demoadmin@demo.example.com", "Demo", "Admin", True, True),
                    ("demomanager", "demomanager@demo.example.com", "Demi", "Manager", False, True),
                    ("demostaff", "demostaff@demo.example.com", "Dana", "Staff", False, False),
                ]
            else:
                users_spec = [
                    ("qaadmin", "qaadmin@qa.example.com", "QA", "Admin", True, True),
                    ("qamanager", "qamanager@qa.example.com", "Quinn", "Manager", False, True),
                    ("qastaff", "qastaff@qa.example.com", "Quincy", "Staff", False, False),
                ]

            profiles = []
            for uname, email, first, last, is_admin, has_staff in users_spec:
                user = ensure_user(uname, email, first, last, password)
                profile, created = OrgUserProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        "organization": org,
                        "title": "Administrator" if is_admin else ("Manager" if has_staff else "Member"),
                        "location": "HQ",
                        "timezone": "UTC",
                        "is_organization_admin": is_admin,
                        "has_staff_panel_access": has_staff,
                        "can_create_organizations": False,
                    },
                )
                # If existed but attached to another org (unlikely here since OneToOne), keep existing
                if created:
                    self.stdout.write(f"  ↳ profile created for {uname} in {org.slug}")
                profiles.append((user, profile, is_admin))

            profiles_by_org[org.id] = profiles

        # 3) Teams and members
        for org in orgs:
            sales, _ = Team.objects.get_or_create(organization=org, name="Sales", defaults={"description": "Sales"})
            service, _ = Team.objects.get_or_create(organization=org, name="Service", defaults={"description": "Service"})
            marketing, _ = Team.objects.get_or_create(organization=org, name="Marketing", defaults={"description": "Marketing"})
            field_service, _ = Team.objects.get_or_create(
                organization=org, name="Field Service", defaults={"description": "On-site service", "parent_team": service}
            )
            # If parent_team wasn't set via defaults due to existing record, ensure it
            if field_service.parent_team is None:
                field_service.parent_team = service
                field_service.save(update_fields=["parent_team"])

            # Assign members
            for user, profile, is_admin in profiles_by_org[org.id]:
                if is_admin:
                    service.manager = profile
                    service.save(update_fields=["manager"])
                    service.members.add(profile)
                else:
                    sales.members.add(profile)
                    marketing.members.add(profile)

        # 4) Ensure permissions/roles per org (best-effort)
        for org in orgs:
            try:
                # Ensure at least one admin profile flag for role assignment
                admin_profile = None
                for _, profile, is_admin in profiles_by_org[org.id]:
                    if is_admin:
                        admin_profile = profile
                        break
                if admin_profile and not admin_profile.is_organization_admin:
                    admin_profile.is_organization_admin = True
                    admin_profile.save(update_fields=["is_organization_admin"])

                call_command("setup_permissions", "--organization-slug", org.slug)
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"(skip) setup_permissions for {org.slug}: {e}"))

        # 5) Job types
        for org in orgs:
            JobType.objects.get_or_create(organization=org, name="Onboarding", defaults={"description": "Employee onboarding"})
            JobType.objects.get_or_create(organization=org, name="Incident", defaults={"description": "Incident handling"})

        # 6) Workflows, steps, transitions, work items (using cflows models)
        from services.cflows.models import Workflow, WorkflowStep, WorkflowTransition, WorkItem, WorkItemHistory

        for org in orgs:
            profiles = profiles_by_org[org.id]
            created_by_profile = next((p for _, p, is_admin in profiles if is_admin), profiles[0][1])
            owner_team = Team.objects.filter(organization=org).order_by("name").first()
            if not owner_team:
                self.stdout.write(self.style.WARNING(f"No teams found for {org.slug}; skipping workflow creation"))
                continue

            wf, _ = Workflow.objects.get_or_create(
                organization=org,
                name="Sample Process",
                defaults={
                    "description": "A sample 4-step workflow",
                    "owner_team": owner_team,
                    "created_by": created_by_profile,
                    "is_active": True,
                },
            )
            # Allow other teams to edit/view
            wf.allowed_edit_teams.add(*Team.objects.filter(organization=org))

            # Steps (idempotent by name within workflow)
            steps_spec = [
                ("New", 1, None, False),
                ("In Progress", 2, owner_team, False),
                ("Review", 3, owner_team, False),
                ("Done", 4, None, True),
            ]
            step_objs = {}
            for name, order, assigned_team, terminal in steps_spec:
                step, _ = WorkflowStep.objects.get_or_create(
                    workflow=wf,
                    name=name,
                    defaults={"order": order, "assigned_team": assigned_team, "is_terminal": terminal},
                )
                # Keep order/terminal up to date
                updates = {}
                if step.order != order:
                    updates["order"] = order
                if step.is_terminal != terminal:
                    updates["is_terminal"] = terminal
                if updates:
                    for k, v in updates.items():
                        setattr(step, k, v)
                    step.save(update_fields=list(updates.keys()))
                step_objs[name] = step

            # Transitions
            transitions = [
                ("New", "In Progress", "Start", "blue"),
                ("In Progress", "Review", "Submit for review", "indigo"),
                ("Review", "Done", "Approve & complete", "green"),
            ]
            for from_name, to_name, label, color in transitions:
                WorkflowTransition.objects.get_or_create(
                    from_step=step_objs[from_name],
                    to_step=step_objs[to_name],
                    defaults={"label": label, "color": color, "order": step_objs[to_name].order},
                )

            # Work items
            items_spec = [
                ("Welcome new employee", "Onboarding steps for new hire", "high"),
                ("Fix login issue", "User cannot login; investigate", "normal"),
                ("Marketing brief", "Draft Q4 campaign brief", "low"),
            ]
            assignees = [p for _, p, _ in profiles]
            for idx, (title, desc, priority) in enumerate(items_spec):
                item, created = WorkItem.objects.get_or_create(
                    workflow=wf,
                    title=title,
                    defaults={
                        "current_step": step_objs["New"],
                        "description": desc,
                        "priority": priority,
                        "created_by": created_by_profile,
                        "current_assignee": assignees[idx % len(assignees)],
                        "due_date": timezone.now() + timezone.timedelta(days=7 + idx),
                        "data": {"seed": True},
                    },
                )
                if created:
                    WorkItemHistory.objects.create(
                        work_item=item,
                        from_step=None,
                        to_step=step_objs["New"],
                        changed_by=created_by_profile,
                        notes="Created",
                        data_snapshot=item.data,
                    )

        self.stdout.write(self.style.SUCCESS("✅ Demo data seeding complete."))
