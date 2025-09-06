from django.core.management.base import BaseCommand
from services.scheduling.services import ResourceManagementService
from core.models import Organization, Team


class Command(BaseCommand):
    help = 'Setup schedulable resources for all teams'

    def add_arguments(self, parser):
        parser.add_argument(
            '--org-id',
            type=int,
            help='Specific organization ID to setup (optional)'
        )

    def handle(self, *args, **options):
        if options['org_id']:
            organizations = Organization.objects.filter(id=options['org_id'])
        else:
            organizations = Organization.objects.all()

        total_created = 0
        
        for org in organizations:
            self.stdout.write(f"Setting up resources for organization: {org.name}")
            
            resource_service = ResourceManagementService(org)
            teams = Team.objects.filter(organization=org, is_active=True)
            
            created_count = 0
            
            for team in teams:
                # Check if resource already exists
                from services.scheduling.models import SchedulableResource
                
                if not SchedulableResource.objects.filter(
                    organization=org,
                    linked_team=team
                ).exists():
                    resource = resource_service.create_resource(
                        name=team.name,
                        resource_type='team',
                        description=f"Team resource for {team.name}",
                        max_concurrent_bookings=team.default_capacity,
                        linked_team=team,
                        service_type='cflows'
                    )
                    
                    # Set default availability (9 AM to 5 PM, Monday to Friday)
                    resource_service.set_resource_availability(
                        resource,
                        start_hour=9,
                        end_hour=17,
                        working_days=[0, 1, 2, 3, 4]  # Mon-Fri
                    )
                    
                    created_count += 1
                    self.stdout.write(f"  Created resource for team: {team.name}")
                else:
                    self.stdout.write(f"  Resource already exists for team: {team.name}")
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created {created_count} new resources for {org.name}"
                )
            )
            
            total_created += created_count

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created {total_created} total resources"
            )
        )