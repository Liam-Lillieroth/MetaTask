from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import CustomUser, Organization, OrganizationMember


class Command(BaseCommand):
    help = 'Create sample users and organizations for testing the registration system'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating sample data...'))

        # Create sample users
        users_data = [
            {
                'username': 'john_doe',
                'email': 'john@example.com',
                'first_name': 'John',
                'last_name': 'Doe',
                'phone_number': '+1234567890',
                'referral_source': 'search',
                'team_size': '2-10',
                'job_title': 'CEO',
                'privacy_policy_accepted': True,
                'terms_accepted': True,
                'privacy_policy_accepted_date': timezone.now(),
                'terms_accepted_date': timezone.now(),
            },
            {
                'username': 'jane_smith',
                'email': 'jane@techcorp.com',
                'first_name': 'Jane',
                'last_name': 'Smith',
                'phone_number': '+1987654321',
                'referral_source': 'referral',
                'team_size': '11-50',
                'job_title': 'CTO',
                'privacy_policy_accepted': True,
                'terms_accepted': True,
                'privacy_policy_accepted_date': timezone.now(),
                'terms_accepted_date': timezone.now(),
            },
            {
                'username': 'mike_wilson',
                'email': 'mike@startup.com',
                'first_name': 'Mike',
                'last_name': 'Wilson',
                'phone_number': '+1555123456',
                'referral_source': 'social_media',
                'team_size': '1',
                'job_title': 'Founder',
                'privacy_policy_accepted': True,
                'terms_accepted': True,
                'privacy_policy_accepted_date': timezone.now(),
                'terms_accepted_date': timezone.now(),
            }
        ]

        created_users = []
        for user_data in users_data:
            user, created = CustomUser.objects.get_or_create(
                username=user_data['username'],
                defaults=user_data
            )
            if created:
                user.set_password('testpass123')
                user.save()
                created_users.append(user)
                self.stdout.write(f'Created user: {user.username}')
            else:
                self.stdout.write(f'User already exists: {user.username}')

        # Create sample organizations
        if created_users:
            orgs_data = [
                {
                    'name': 'Acme Corporation',
                    'owner': created_users[0] if len(created_users) > 0 else None,
                    'company_type': 'smb',
                    'purpose': 'project_management',
                    'team_size': '2-10',
                    'description': 'A leading software development company',
                    'website': 'https://acme.com',
                    'contact_email': 'info@acme.com',
                    'contact_phone': '+1234567890',
                    'address_line1': '123 Business St',
                    'city': 'Tech City',
                    'state': 'CA',
                    'postal_code': '12345',
                    'country': 'USA'
                },
                {
                    'name': 'TechCorp Solutions',
                    'owner': created_users[1] if len(created_users) > 1 else None,
                    'company_type': 'enterprise',
                    'purpose': 'development',
                    'team_size': '11-50',
                    'description': 'Enterprise technology solutions provider',
                    'website': 'https://techcorp.com',
                    'contact_email': 'contact@techcorp.com',
                    'contact_phone': '+1987654321',
                    'address_line1': '456 Innovation Blvd',
                    'city': 'Silicon Valley',
                    'state': 'CA',
                    'postal_code': '94000',
                    'country': 'USA'
                },
                {
                    'name': 'StartupX',
                    'owner': created_users[2] if len(created_users) > 2 else None,
                    'company_type': 'startup',
                    'purpose': 'marketing',
                    'team_size': '1',
                    'description': 'Revolutionary startup changing the world',
                    'website': 'https://startupx.com',
                    'contact_email': 'hello@startupx.com',
                    'contact_phone': '+1555123456',
                    'address_line1': '789 Startup Ave',
                    'city': 'Austin',
                    'state': 'TX',
                    'postal_code': '73301',
                    'country': 'USA'
                }
            ]

            for org_data in orgs_data:
                if org_data['owner']:
                    org, created = Organization.objects.get_or_create(
                        name=org_data['name'],
                        defaults=org_data
                    )
                    if created:
                        # Create organization membership for the owner
                        OrganizationMember.objects.get_or_create(
                            organization=org,
                            user=org_data['owner'],
                            defaults={'role': 'owner'}
                        )
                        self.stdout.write(f'Created organization: {org.name}')
                    else:
                        self.stdout.write(f'Organization already exists: {org.name}')

        self.stdout.write(self.style.SUCCESS('Sample data creation completed!'))
        self.stdout.write('Test users created with password: testpass123')
        self.stdout.write('You can now test the registration system and admin interface.')
