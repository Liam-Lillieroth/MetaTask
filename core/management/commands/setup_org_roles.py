"""
Management command to set up default organizational roles and permissions
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Organization
from core.permissions import Permission, Role, RolePermission


class Command(BaseCommand):
    help = 'Set up default organizational roles and permissions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--organization',
            type=str,
            help='Organization slug to set up roles for',
        )

    def handle(self, *args, **options):
        organization_slug = options.get('organization')
        
        if organization_slug:
            try:
                organization = Organization.objects.get(slug=organization_slug)
                self.setup_organization_roles(organization)
            except Organization.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Organization with slug "{organization_slug}" not found')
                )
                return
        else:
            # Set up for all organizations
            for organization in Organization.objects.all():
                self.setup_organization_roles(organization)

    @transaction.atomic
    def setup_organization_roles(self, organization):
        """Set up default roles for an organization"""
        self.stdout.write(f'Setting up roles for {organization.name}...')
        
        # Create default permissions if they don't exist
        permissions = self.create_default_permissions()
        
        # Create default roles
        roles = self.create_default_roles(organization)
        
        # Assign permissions to roles
        self.assign_permissions_to_roles(roles, permissions)
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully set up roles for {organization.name}')
        )

    def create_default_permissions(self):
        """Create default permissions"""
        permissions_data = [
            # User management permissions
            {
                'codename': 'user.create',
                'name': 'Create Users',
                'description': 'Can create new user accounts',
                'category': 'user'
            },
            {
                'codename': 'user.edit',
                'name': 'Edit Users',
                'description': 'Can edit user profiles and information',
                'category': 'user'
            },
            {
                'codename': 'user.deactivate',
                'name': 'Deactivate Users',
                'description': 'Can deactivate user accounts',
                'category': 'user'
            },
            {
                'codename': 'user.assign_roles',
                'name': 'Assign Roles',
                'description': 'Can assign roles to users',
                'category': 'user'
            },
            
            # Team management permissions
            {
                'codename': 'team.create',
                'name': 'Create Teams',
                'description': 'Can create new teams',
                'category': 'team'
            },
            {
                'codename': 'team.edit',
                'name': 'Edit Teams',
                'description': 'Can edit team information and membership',
                'category': 'team'
            },
            {
                'codename': 'team.delete',
                'name': 'Delete Teams',
                'description': 'Can delete teams',
                'category': 'team'
            },
            
            # Workflow permissions
            {
                'codename': 'workflow.create',
                'name': 'Create Workflows',
                'description': 'Can create new workflows',
                'category': 'workflow'
            },
            {
                'codename': 'workflow.edit',
                'name': 'Edit Workflows',
                'description': 'Can edit workflow configurations',
                'category': 'workflow'
            },
            {
                'codename': 'workflow.delete',
                'name': 'Delete Workflows',
                'description': 'Can delete workflows',
                'category': 'workflow'
            },
            
            # Reporting permissions
            {
                'codename': 'reporting.view',
                'name': 'View Reports',
                'description': 'Can view analytics and reports',
                'category': 'reporting'
            },
            {
                'codename': 'reporting.export',
                'name': 'Export Reports',
                'description': 'Can export reports and data',
                'category': 'reporting'
            },
        ]
        
        permissions = {}
        for perm_data in permissions_data:
            permission, created = Permission.objects.get_or_create(
                codename=perm_data['codename'],
                defaults={
                    'name': perm_data['name'],
                    'description': perm_data['description'],
                    'category': perm_data['category']
                }
            )
            permissions[perm_data['codename']] = permission
            if created:
                self.stdout.write(f'  Created permission: {permission.name}')
        
        return permissions

    def create_default_roles(self, organization):
        """Create default roles for the organization"""
        roles_data = [
            {
                'name': 'Organization Admin',
                'description': 'Full administrative access to the organization',
                'color': '#DC2626'  # Red
            },
            {
                'name': 'HR Manager',
                'description': 'Manages users and teams within assigned locations',
                'color': '#059669'  # Green
            },
            {
                'name': 'Team Lead',
                'description': 'Manages a specific team and its workflows',
                'color': '#2563EB'  # Blue
            },
            {
                'name': 'Department Manager',
                'description': 'Manages users and workflows within a department',
                'color': '#7C3AED'  # Purple
            },
            {
                'name': 'Location Supervisor',
                'description': 'Oversees operations at a specific location',
                'color': '#EA580C'  # Orange
            },
            {
                'name': 'Standard User',
                'description': 'Basic user with standard access',
                'color': '#6B7280',  # Gray
                'is_default': True
            }
        ]
        
        roles = {}
        for role_data in roles_data:
            role, created = Role.objects.get_or_create(
                organization=organization,
                name=role_data['name'],
                defaults={
                    'description': role_data['description'],
                    'color': role_data['color'],
                    'is_default': role_data.get('is_default', False)
                }
            )
            roles[role_data['name']] = role
            if created:
                self.stdout.write(f'  Created role: {role.name}')
        
        return roles

    def assign_permissions_to_roles(self, roles, permissions):
        """Assign permissions to roles"""
        
        # Organization Admin - all permissions
        admin_role = roles['Organization Admin']
        for permission in permissions.values():
            RolePermission.objects.get_or_create(
                role=admin_role,
                permission=permission
            )
        
        # HR Manager - user and team management
        hr_role = roles['HR Manager']
        hr_permissions = [
            'user.create', 'user.edit', 'user.deactivate', 'user.assign_roles',
            'team.create', 'team.edit', 'reporting.view'
        ]
        for perm_code in hr_permissions:
            if perm_code in permissions:
                RolePermission.objects.get_or_create(
                    role=hr_role,
                    permission=permissions[perm_code]
                )
        
        # Team Lead - team and workflow management
        team_lead_role = roles['Team Lead']
        team_lead_permissions = [
            'team.edit', 'workflow.create', 'workflow.edit', 'reporting.view'
        ]
        for perm_code in team_lead_permissions:
            if perm_code in permissions:
                RolePermission.objects.get_or_create(
                    role=team_lead_role,
                    permission=permissions[perm_code]
                )
        
        # Department Manager - broader management within department
        dept_manager_role = roles['Department Manager']
        dept_permissions = [
            'user.create', 'user.edit', 'team.create', 'team.edit',
            'workflow.create', 'workflow.edit', 'reporting.view', 'reporting.export'
        ]
        for perm_code in dept_permissions:
            if perm_code in permissions:
                RolePermission.objects.get_or_create(
                    role=dept_manager_role,
                    permission=permissions[perm_code]
                )
        
        # Location Supervisor - location oversight
        location_role = roles['Location Supervisor']
        location_permissions = [
            'team.edit', 'workflow.edit', 'reporting.view'
        ]
        for perm_code in location_permissions:
            if perm_code in permissions:
                RolePermission.objects.get_or_create(
                    role=location_role,
                    permission=permissions[perm_code]
                )
        
        self.stdout.write('  Assigned permissions to roles')
