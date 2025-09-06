from django.core.management.base import BaseCommand
from services.scheduling.integrations import get_service_integration
from core.models import Organization


class Command(BaseCommand):
    help = 'Sync CFlows team bookings to the scheduling system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--org-id',
            type=int,
            help='Specific organization ID to sync (optional)'
        )

    def handle(self, *args, **options):
        if options['org_id']:
            organizations = Organization.objects.filter(id=options['org_id'])
        else:
            organizations = Organization.objects.all()

        total_synced = 0
        
        for org in organizations:
            self.stdout.write(f"Syncing organization: {org.name}")
            
            integration = get_service_integration(org, 'cflows')
            synced_bookings = integration.sync_all_team_bookings()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"Synced {len(synced_bookings)} bookings for {org.name}"
                )
            )
            
            total_synced += len(synced_bookings)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully synced {total_synced} total bookings"
            )
        )