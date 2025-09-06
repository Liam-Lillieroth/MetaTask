"""
Management command to sync existing CFlows team bookings with scheduling service
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from services.cflows.scheduling_integration import CFlowsSchedulingIntegration
from core.models import Organization


class Command(BaseCommand):
    help = 'Sync existing CFlows team bookings with scheduling service'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--organization',
            type=str,
            help='Organization name to sync (if not provided, syncs all organizations)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without making changes',
        )
    
    def handle(self, *args, **options):
        organization_name = options.get('organization')
        dry_run = options.get('dry_run', False)
        
        # Get organization if specified
        organization = None
        if organization_name:
            try:
                organization = Organization.objects.get(name=organization_name)
                self.stdout.write(f"Syncing bookings for organization: {organization.name}")
            except Organization.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"Organization '{organization_name}' not found")
                )
                return
        else:
            self.stdout.write("Syncing bookings for all organizations")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))
            return
        
        try:
            with transaction.atomic():
                synced_count, error_count = CFlowsSchedulingIntegration.sync_existing_bookings(
                    organization=organization
                )
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully synced {synced_count} bookings"
                    )
                )
                
                if error_count > 0:
                    self.stdout.write(
                        self.style.WARNING(
                            f"{error_count} bookings had errors during sync"
                        )
                    )
                    
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error during sync: {str(e)}")
            )
