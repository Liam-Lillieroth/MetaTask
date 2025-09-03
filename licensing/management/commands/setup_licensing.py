from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from licensing.models import Service, LicenseType, License
from core.models import Organization


class Command(BaseCommand):
    help = 'Set up initial licensing data for Mediap services'

    def handle(self, *args, **options):
        self.stdout.write('Setting up initial licensing data...')
        
        # Create CFlows service
        cflows_service, created = Service.objects.get_or_create(
            slug='cflows',
            defaults={
                'name': 'CFlows',
                'description': 'Workflow Management System',
                'version': '1.0.0',
                'is_active': True,
                'icon': 'fas fa-project-diagram',
                'color': '#2563eb',
                'sort_order': 1,
                'allows_personal_free': True,
                'personal_free_limits': {
                    'users': 1,
                    'workflows': 3,
                    'work_items': 100,
                    'projects': 2
                }
            }
        )
        
        if created:
            self.stdout.write(f'✓ Created CFlows service')
        else:
            self.stdout.write(f'✓ CFlows service already exists')
        
        # Create license types for CFlows
        license_types_data = [
            {
                'name': 'personal_free',
                'display_name': 'Personal Free',
                'price_monthly': Decimal('0.00'),
                'price_yearly': Decimal('0.00'),
                'max_users': 1,
                'max_projects': 2,
                'max_workflows': 3,
                'max_storage_gb': 1,
                'max_api_calls_per_day': 100,
                'features': ['Basic workflows', 'Personal workspace', 'Email notifications'],
                'restrictions': ['No team collaboration', 'Limited integrations'],
                'is_personal_only': True,
                'requires_organization': False
            },
            {
                'name': 'basic',
                'display_name': 'Basic Team',
                'price_monthly': Decimal('29.00'),
                'price_yearly': Decimal('290.00'),
                'max_users': 10,
                'max_projects': 10,
                'max_workflows': 25,
                'max_storage_gb': 10,
                'max_api_calls_per_day': 1000,
                'features': ['Team collaboration', 'Custom workflows', 'Basic integrations', 'Email & SMS notifications'],
                'restrictions': ['Limited admin features'],
                'is_personal_only': False,
                'requires_organization': True
            },
            {
                'name': 'professional',
                'display_name': 'Professional',
                'price_monthly': Decimal('79.00'),
                'price_yearly': Decimal('790.00'),
                'max_users': 50,
                'max_projects': 50,
                'max_workflows': 100,
                'max_storage_gb': 100,
                'max_api_calls_per_day': 10000,
                'features': ['Advanced workflows', 'All integrations', 'Advanced analytics', 'Priority support'],
                'restrictions': [],
                'is_personal_only': False,
                'requires_organization': True
            },
            {
                'name': 'enterprise',
                'display_name': 'Enterprise',
                'price_monthly': Decimal('299.00'),
                'price_yearly': Decimal('2990.00'),
                'max_users': None,  # Unlimited
                'max_projects': None,
                'max_workflows': None,
                'max_storage_gb': None,
                'max_api_calls_per_day': None,
                'features': ['Unlimited everything', 'Custom integrations', 'Dedicated support', 'SLA guarantee'],
                'restrictions': [],
                'is_personal_only': False,
                'requires_organization': True
            }
        ]
        
        for lt_data in license_types_data:
            license_type, created = LicenseType.objects.get_or_create(
                service=cflows_service,
                name=lt_data['name'],
                defaults=lt_data
            )
            
            if created:
                self.stdout.write(f'✓ Created license type: {lt_data["display_name"]}')
            else:
                self.stdout.write(f'✓ License type already exists: {lt_data["display_name"]}')
        
        # Set up personal free licenses for personal organizations
        personal_orgs = Organization.objects.filter(organization_type='personal')
        personal_free_license_type = LicenseType.objects.get(
            service=cflows_service, 
            name='personal_free'
        )
        
        for org in personal_orgs:
            license, created = License.objects.get_or_create(
                organization=org,
                license_type=personal_free_license_type,
                defaults={
                    'account_type': 'personal',
                    'is_personal_free': True,
                    'status': 'active',
                    'billing_cycle': 'lifetime',
                    'start_date': timezone.now(),
                    'current_users': org.members.count(),
                }
            )
            
            if created:
                self.stdout.write(f'✓ Created personal free license for: {org.name}')
        
        # Update existing Demo Car Dealership organization to be business type with basic license
        try:
            demo_org = Organization.objects.get(name='Demo Car Dealership')
            if demo_org.organization_type != 'business':
                demo_org.organization_type = 'business'
                demo_org.save()
                self.stdout.write(f'✓ Updated {demo_org.name} to business organization')
            
            basic_license_type = LicenseType.objects.get(
                service=cflows_service,
                name='basic'
            )
            
            license, created = License.objects.get_or_create(
                organization=demo_org,
                license_type=basic_license_type,
                defaults={
                    'account_type': 'organization',
                    'is_personal_free': False,
                    'status': 'trial',
                    'billing_cycle': 'monthly',
                    'start_date': timezone.now(),
                    'trial_end_date': timezone.now() + timezone.timedelta(days=30),
                    'current_users': demo_org.members.count(),
                    'current_workflows': demo_org.workflows.count() if hasattr(demo_org, 'workflows') else 0,
                }
            )
            
            if created:
                self.stdout.write(f'✓ Created basic trial license for: {demo_org.name}')
                
        except Organization.DoesNotExist:
            self.stdout.write('⚠ Demo Car Dealership organization not found')
        
        self.stdout.write(
            self.style.SUCCESS('Successfully set up initial licensing data!')
        )
