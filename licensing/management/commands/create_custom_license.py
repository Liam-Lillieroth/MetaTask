from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.contrib.auth import get_user_model
from core.models import Organization
from licensing.models import Service, CustomLicense, License, LicenseType, LicenseAuditLog
from datetime import datetime, timedelta

User = get_user_model()


class Command(BaseCommand):
    help = 'Create custom licenses for organizations (Customer Support Tool)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--organization',
            type=str,
            required=True,
            help='Organization name or ID'
        )
        parser.add_argument(
            '--service',
            type=str,
            required=True,
            help='Service slug (e.g., cflows, scheduling)'
        )
        parser.add_argument(
            '--users',
            type=int,
            required=True,
            help='Maximum number of users'
        )
        parser.add_argument(
            '--name',
            type=str,
            help='Custom license name (auto-generated if not provided)'
        )
        parser.add_argument(
            '--duration',
            type=int,
            default=365,
            help='License duration in days (default: 365, 0 for unlimited)'
        )
        parser.add_argument(
            '--features',
            type=str,
            nargs='*',
            default=[],
            help='Additional features to include'
        )
        parser.add_argument(
            '--created-by',
            type=str,
            help='Username of the customer support person creating this license'
        )
        parser.add_argument(
            '--activate',
            action='store_true',
            help='Automatically activate the license and create License instance'
        )

    def handle(self, *args, **options):
        # Get organization
        org_identifier = options['organization']
        try:
            # Try to get by ID first, then by name
            if org_identifier.isdigit():
                organization = Organization.objects.get(id=int(org_identifier))
            else:
                organization = Organization.objects.get(name__icontains=org_identifier)
        except Organization.DoesNotExist:
            raise CommandError(f'Organization "{org_identifier}" not found')
        except Organization.MultipleObjectsReturned:
            organizations = Organization.objects.filter(name__icontains=org_identifier)
            org_names = [org.name for org in organizations]
            raise CommandError(f'Multiple organizations found: {", ".join(org_names)}. Please be more specific.')

        # Get service
        service_slug = options['service']
        try:
            service = Service.objects.get(slug=service_slug)
        except Service.DoesNotExist:
            available_services = Service.objects.filter(is_active=True).values_list('slug', flat=True)
            raise CommandError(f'Service "{service_slug}" not found. Available services: {", ".join(available_services)}')

        # Get created_by user
        created_by_user = None
        if options['created_by']:
            try:
                created_by_user = User.objects.get(username=options['created_by'])
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'User "{options["created_by"]}" not found. License will be created without creator reference.')
                )

        # Generate license name if not provided
        license_name = options['name']
        if not license_name:
            license_name = f"{organization.name} - {service.name} Custom License"

        # Calculate end date
        start_date = timezone.now()
        end_date = None
        if options['duration'] > 0:
            end_date = start_date + timedelta(days=options['duration'])

        # Create custom license
        try:
            custom_license = CustomLicense.objects.create(
                name=license_name,
                organization=organization,
                service=service,
                max_users=options['users'],
                description=f"Custom license created for {organization.name}",
                start_date=start_date,
                end_date=end_date,
                is_active=True,
                included_features=options['features'],
                restrictions={},
                created_by=created_by_user,
                notes=f"Created via management command on {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

            self.stdout.write(
                self.style.SUCCESS(f'✓ Created custom license: {custom_license.name}')
            )
            self.stdout.write(f'  Organization: {organization.name}')
            self.stdout.write(f'  Service: {service.name}')
            self.stdout.write(f'  Max Users: {options["users"]}')
            self.stdout.write(f'  Duration: {"Unlimited" if not end_date else f"{options["duration"]} days"}')
            
            if options['features']:
                self.stdout.write(f'  Features: {", ".join(options["features"])}')

            # Create audit log
            LicenseAuditLog.objects.create(
                custom_license=custom_license,
                action='create',
                performed_by=created_by_user,
                description=f'Custom license created via management command',
                new_values={
                    'name': license_name,
                    'max_users': options['users'],
                    'duration_days': options['duration'],
                    'features': options['features']
                }
            )

            # Auto-activate if requested
            if options['activate']:
                # Check if organization already has a license for this service
                existing_licenses = License.objects.filter(
                    organization=organization,
                    license_type__service=service,
                    status__in=['active', 'trial']
                )
                
                if existing_licenses.exists():
                    self.stdout.write(
                        self.style.WARNING(f'⚠ Organization already has active licenses for {service.name}:')
                    )
                    for license in existing_licenses:
                        self.stdout.write(f'  - {license.license_type.display_name} ({license.status})')
                    
                    response = input('Do you want to create an additional license instance? (y/N): ')
                    if response.lower() != 'y':
                        self.stdout.write('Custom license created but not activated.')
                        return

                # Create a "custom" license type if it doesn't exist
                custom_license_type, created = LicenseType.objects.get_or_create(
                    service=service,
                    name='custom',
                    defaults={
                        'display_name': 'Custom License',
                        'price_monthly': 0,
                        'price_yearly': 0,
                        'max_users': None,  # Will be controlled by CustomLicense
                        'features': ['custom_configuration'],
                        'is_active': True
                    }
                )

                # Create License instance
                license_instance = License.objects.create(
                    license_type=custom_license_type,
                    organization=organization,
                    custom_license=custom_license,
                    account_type='organization',
                    status='active',
                    start_date=start_date,
                    end_date=end_date,
                    current_users=0,
                    created_by=created_by_user
                )

                self.stdout.write(
                    self.style.SUCCESS(f'✓ Activated license instance: {license_instance}')
                )

                # Create audit log for activation
                LicenseAuditLog.objects.create(
                    license=license_instance,
                    custom_license=custom_license,
                    action='create',
                    performed_by=created_by_user,
                    description=f'License instance activated for custom license',
                    new_values={
                        'license_id': str(license_instance.id),
                        'status': 'active'
                    }
                )

        except Exception as e:
            raise CommandError(f'Error creating custom license: {str(e)}')

        self.stdout.write(
            self.style.SUCCESS(f'✓ Custom license setup completed!')
        )
