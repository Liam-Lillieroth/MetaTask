"""
Management command to set up default permissions and roles for organizations
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from accounts.models import Organization
from core.services.permission_service import PermissionService


class Command(BaseCommand):
    help = 'Set up default permissions and roles for an organization'

    def add_arguments(self, parser):
        parser.add_argument(
            '--organization-id',
            type=int,
            help='Organization ID to set up permissions for'
        )
        parser.add_argument(
            '--organization-slug',
            type=str,
            help='Organization slug to set up permissions for'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Set up permissions for all organizations'
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset existing permissions and roles (destructive!)'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        organizations = []
        
        if options['all']:
            organizations = Organization.objects.filter(is_active=True)
            self.stdout.write(
                self.style.WARNING(
                    f"Setting up permissions for {organizations.count()} organizations..."
                )
            )
        elif options['organization_id']:
            try:
                org = Organization.objects.get(id=options['organization_id'])
                organizations = [org]
            except Organization.DoesNotExist:
                raise CommandError(f"Organization with ID {options['organization_id']} does not exist")
        elif options['organization_slug']:
            try:
                org = Organization.objects.get(slug=options['organization_slug'])
                organizations = [org]
            except Organization.DoesNotExist:
                raise CommandError(f"Organization with slug '{options['organization_slug']}' does not exist")
        else:
            raise CommandError("Please specify --organization-id, --organization-slug, or --all")
        
        if not organizations:
            self.stdout.write(self.style.ERROR("No organizations found to set up"))
            return
        
        for organization in organizations:
            self.stdout.write(
                self.style.SUCCESS(f"Setting up permissions for: {organization.name}")
            )
            
            try:
                permission_service = PermissionService(organization)
                
                # Create default permissions
                self.stdout.write("Creating default permissions...")
                permissions = permission_service.create_default_permissions()
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Created/verified {len(permissions)} permissions")
                )
                
                # Create default roles
                self.stdout.write("Creating default roles...")
                roles = permission_service.create_default_roles()
                role_names = [role.name for role in roles]
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Created/verified roles: {', '.join(role_names)}")
                )
                
                # Assign organization owner admin role
                if organization.owner and hasattr(organization.owner, 'profile'):
                    admin_role = next((r for r in roles if 'Administrator' in r.name), None)
                    if admin_role:
                        permission_service.assign_role_to_user(
                            user_profile=organization.owner.profile,
                            role=admin_role,
                            assigned_by=organization.owner.profile,
                            notes="Auto-assigned to organization owner"
                        )
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"✓ Assigned admin role to organization owner: {organization.owner.username}"
                            )
                        )
                    
                    # Set organization admin flag
                    organization.owner.profile.is_organization_admin = True
                    organization.owner.profile.save()
                
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Completed setup for {organization.name}\n")
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"✗ Error setting up {organization.name}: {str(e)}")
                )
                if options['verbosity'] > 1:
                    import traceback
                    traceback.print_exc()
        
        self.stdout.write(
            self.style.SUCCESS("Permission setup completed successfully!")
        )
