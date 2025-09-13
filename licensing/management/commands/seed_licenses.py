"""
Seed licensing demo data: ensure services and license types, create standard and
optional custom licenses for target organizations, and assign users to seats.
Idempotent and safe to run multiple times.
"""

from datetime import timedelta
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import transaction
from django.utils import timezone

from licensing.models import Service, LicenseType, License, CustomLicense, UserLicenseAssignment
from licensing.services import LicensingService
from core.models import Organization


class Command(BaseCommand):
    help = "Seed demo licensing: services, license types, licenses, and user assignments"

    def add_arguments(self, parser):
        parser.add_argument(
            "--org-slug",
            action="append",
            default=[],
            help="Organization slug(s) to seed (repeatable). Defaults to demo-corp and qa-sandbox.",
        )
        parser.add_argument(
            "--users-per-license",
            type=int,
            default=5,
            help="Max users to assign per license",
        )
        parser.add_argument(
            "--trial-days",
            type=int,
            default=30,
            help="Trial period length in days for trial licenses",
        )
        parser.add_argument(
            "--include-custom",
            action="store_true",
            help="Also create a custom license per org and assign users",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Remove existing licenses and assignments for target orgs before seeding",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        org_slugs = opts.get("org_slug", [])
        if not org_slugs:
            org_slugs = ["demo-corp", "qa-sandbox"]
        users_per_license = opts["users_per_license"]
        trial_days = opts["trial_days"]
        include_custom = opts["include_custom"]
        do_reset = opts["reset"]

        self.stdout.write(self.style.MIGRATE_HEADING("Seeding licensing demo data..."))

        # 1) Ensure base licensing data exists
        call_command("setup_licensing")

        # Resolve services
        cflows = Service.objects.get(slug="cflows")
        scheduling = Service.objects.get(slug="scheduling")

        # Resolve license types we will use
        lt_map = {
            ("cflows", "personal_free"): LicenseType.objects.get(service=cflows, name="personal_free"),
            ("cflows", "basic"): LicenseType.objects.get(service=cflows, name="basic"),
            ("cflows", "professional"): LicenseType.objects.get(service=cflows, name="professional"),
            ("cflows", "enterprise"): LicenseType.objects.get(service=cflows, name="enterprise"),
            ("scheduling", "personal_free"): LicenseType.objects.get(service=scheduling, name="personal_free"),
            ("scheduling", "basic"): LicenseType.objects.get(service=scheduling, name="basic"),
            ("scheduling", "professional"): LicenseType.objects.get(service=scheduling, name="professional"),
            ("scheduling", "enterprise"): LicenseType.objects.get(service=scheduling, name="enterprise"),
        }

        # Ensure a 'custom' license type exists for cflows (used to back custom licenses)
        custom_lt_cflows, _ = LicenseType.objects.get_or_create(
            service=cflows,
            name='custom',
            defaults={
                'display_name': 'Custom',
                'price_monthly': 0,
                'price_yearly': 0,
                'max_users': None,
                'max_projects': None,
                'max_workflows': None,
                'max_storage_gb': None,
                'max_api_calls_per_day': None,
                'features': ['Custom terms'],
                'restrictions': [],
                'is_personal_only': False,
                'requires_organization': True,
            }
        )
        lt_map[("cflows", "custom")] = custom_lt_cflows

        # 2) Target organizations
        orgs = list(Organization.objects.filter(slug__in=org_slugs))
        missing = set(org_slugs) - set(o.slug for o in orgs)
        for slug in missing:
            org = Organization.objects.create(
                name=slug.replace("-", " ").title(),
                slug=slug,
                organization_type="business",
                is_active=True,
            )
            orgs.append(org)
            self.stdout.write(self.style.SUCCESS(f"✓ Created org: {org.name}"))

        if do_reset:
            for org in orgs:
                self._reset_org(org)
            self.stdout.write(self.style.WARNING("Cleared existing licenses and assignments for target orgs."))

        # 3) Create licenses and assign users
        for org in orgs:
            self.stdout.write(f"→ Organization: {org.name} ({org.slug})")

            now = timezone.now()

            # Active basic licenses (standard)
            basic_cflows, _ = License.objects.get_or_create(
                organization=org,
                license_type=lt_map[("cflows", "basic")],
                defaults={
                    "status": "active",
                    "billing_cycle": "monthly",
                    "start_date": now,
                    "end_date": now + timedelta(days=365),
                },
            )
            basic_sched, _ = License.objects.get_or_create(
                organization=org,
                license_type=lt_map[("scheduling", "basic")],
                defaults={
                    "status": "active",
                    "billing_cycle": "monthly",
                    "start_date": now,
                    "end_date": now + timedelta(days=365),
                },
            )

            # Trial professional (standard)
            trial_cflows, _ = License.objects.get_or_create(
                organization=org,
                license_type=lt_map[("cflows", "professional")],
                defaults={
                    "status": "trial",
                    "billing_cycle": "monthly",
                    "start_date": now,
                    "trial_end_date": now + timedelta(days=trial_days),
                },
            )
            trial_sched, _ = License.objects.get_or_create(
                organization=org,
                license_type=lt_map[("scheduling", "professional")],
                defaults={
                    "status": "trial",
                    "billing_cycle": "monthly",
                    "start_date": now,
                    "trial_end_date": now + timedelta(days=trial_days),
                },
            )

            # Optional custom license linked with a License instance
            custom_license_obj = None
            if include_custom:
                custom_license_obj, _ = CustomLicense.objects.get_or_create(
                    organization=org,
                    service=cflows,
                    name="VIP Bundle",
                    defaults={
                        "max_users": 25,
                        "description": "Priority access and support",
                        "start_date": now,
                        "end_date": now + timedelta(days=365),
                        "is_active": True,
                        "included_features": ["VIP support", "Custom integrations"],
                        "restrictions": {},
                    },
                )
                # Attach a standard License row to the custom license for seat tracking
                try:
                    _ = custom_license_obj.license_instance
                    has_backing = True
                except License.DoesNotExist:
                    has_backing = False
                except Exception:
                    has_backing = False
                if not has_backing:
                    # Use 'custom' license type to avoid unique (org, type) conflicts
                    backing_type = lt_map[("cflows", "custom")]
                    License.objects.create(
                        organization=org,
                        license_type=backing_type,
                        custom_license=custom_license_obj,
                        status="active",
                        billing_cycle="yearly",
                        start_date=now,
                        end_date=now + timedelta(days=365),
                    )

            # Assign users to licenses
            admin_profile = org.members.filter(is_organization_admin=True, is_active=True).first()
            assigned_by_user = admin_profile.user if admin_profile else None

            def assign_to_available_users(license_obj: License, max_users: int):
                if not assigned_by_user:
                    return 0
                count = 0
                ls = LicensingService()
                for up in org.members.filter(is_active=True).select_related("user"):
                    if count >= max_users:
                        break
                    ok, _res = ls.assign_user_to_license(license_obj, up, assigned_by_user)
                    if ok:
                        count += 1
                return count

            total_assigned = 0
            for lic in (basic_cflows, basic_sched, trial_cflows, trial_sched):
                total_assigned += assign_to_available_users(lic, users_per_license)

            # Assign to custom (if created)
            if include_custom and custom_license_obj:
                try:
                    lic_inst = custom_license_obj.license_instance
                except License.DoesNotExist:
                    lic_inst = None
                except Exception:
                    lic_inst = None
                if lic_inst:
                    total_assigned += assign_to_available_users(lic_inst, users_per_license)

            self.stdout.write(self.style.SUCCESS(f"✓ {org.slug}: licenses ready, users assigned: {total_assigned}"))

        self.stdout.write(self.style.SUCCESS("✔ Licensing demo data seeding complete."))

    def _reset_org(self, org: Organization):
        # Delete assignments, then licenses, then custom licenses
        assignments = UserLicenseAssignment.objects.filter(license__organization=org)
        assignments.delete()
        License.objects.filter(organization=org).delete()
        CustomLicense.objects.filter(organization=org).delete()
