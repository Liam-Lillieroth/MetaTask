"""
Management command to sync already completed scheduling bookings with CFlows team bookings
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from services.scheduling.models import BookingRequest
from services.cflows.models import TeamBooking, WorkItem
from services.cflows.scheduling_integration import CFlowsSchedulingIntegration


class Command(BaseCommand):
    help = 'Sync already completed scheduling bookings with CFlows team bookings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
        parser.add_argument(
            '--organization-id',
            type=int,
            help='Only sync bookings for a specific organization ID',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        org_id = options.get('organization_id')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Find completed scheduling bookings that originated from CFlows
        completed_bookings = BookingRequest.objects.filter(
            source_service='cflows',
            source_object_type='TeamBooking',
            status='completed'  # Note: using 'completed' not 'complete'
        )
        
        if org_id:
            # Filter by organization if specified
            completed_bookings = completed_bookings.filter(
                organization_id=org_id
            )
        
        self.stdout.write(f'Found {completed_bookings.count()} completed scheduling bookings from CFlows')
        
        synced_count = 0
        error_count = 0
        already_complete_count = 0
        not_found_count = 0
        
        for booking in completed_bookings:
            try:
                # Check if the corresponding TeamBooking exists and is not already complete
                team_booking = TeamBooking.objects.get(id=booking.source_object_id)
                
                if team_booking.is_completed:
                    already_complete_count += 1
                    self.stdout.write(f'  TeamBooking {team_booking.id} already complete - skipping')
                    continue
                
                if dry_run:
                    self.stdout.write(f'  Would mark TeamBooking {team_booking.id} as complete')
                    synced_count += 1
                else:
                    # Mark as complete
                    team_booking.is_completed = True
                    team_booking.completed_at = booking.updated_at or timezone.now()
                    
                    # Add completion notes if they exist
                    completion_notes = booking.custom_data.get('completion_notes', '')
                    if completion_notes and team_booking.work_item:
                        from services.cflows.models import WorkItemComment
                        WorkItemComment.objects.create(
                            work_item=team_booking.work_item,
                            author=None,  # System comment
                            content=f"Booking completion notes: {completion_notes}",
                            is_system_comment=True
                        )
                    
                    team_booking.save()
                    
                    # Check if we should auto-complete the work item
                    if team_booking.work_item:
                        work_item = team_booking.work_item
                        all_bookings = TeamBooking.objects.filter(work_item=work_item)
                        incomplete_bookings = all_bookings.filter(is_completed=False)
                        
                        if not incomplete_bookings.exists() and not work_item.is_completed:
                            # All bookings complete - try to auto-complete work item
                            from services.cflows.models import WorkflowTransition
                            transitions = WorkflowTransition.objects.filter(
                                from_step=work_item.current_step,
                                requires_booking=False
                            ).first()
                            
                            if transitions and transitions.to_step.is_terminal:
                                work_item.current_step = transitions.to_step
                                work_item.is_completed = True
                                work_item.completed_at = timezone.now()
                                work_item.save()
                                self.stdout.write(f'    Auto-completed work item {work_item.id}')
                    
                    synced_count += 1
                    self.stdout.write(f'  ✅ Synced TeamBooking {team_booking.id}')
                    
            except TeamBooking.DoesNotExist:
                not_found_count += 1
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'  ❌ TeamBooking {booking.source_object_id} not found for booking {booking.id}')
                )
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'  ❌ Error syncing booking {booking.id}: {str(e)}')
                )
        
        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(f'SYNC SUMMARY:')
        self.stdout.write(f'  • Synced: {synced_count}')
        self.stdout.write(f'  • Already complete: {already_complete_count}')
        self.stdout.write(f'  • Not found: {not_found_count}')
        self.stdout.write(f'  • Errors: {error_count}')
        
        if dry_run:
            self.stdout.write(f'\nTo apply these changes, run without --dry-run')
        else:
            self.stdout.write(self.style.SUCCESS(f'\n✅ Sync completed successfully!'))
