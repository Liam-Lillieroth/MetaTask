"""
Management command to refresh booking titles to include work item information
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from services.cflows.models import TeamBooking
from services.scheduling.models import BookingRequest


class Command(BaseCommand):
    help = 'Refresh booking titles to include work item information'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        updated_count = 0
        error_count = 0
        
        # Get all TeamBookings that have corresponding BookingRequests
        booking_requests = BookingRequest.objects.filter(
            source_service='cflows',
            source_object_type='TeamBooking'
        ).select_related()
        
        self.stdout.write(f'Found {booking_requests.count()} CFlows bookings to potentially update...')
        
        for booking_request in booking_requests:
            try:
                # Get the corresponding TeamBooking
                team_booking_id = int(booking_request.source_object_id)
                team_booking = TeamBooking.objects.select_related('work_item', 'work_item__workflow', 'team').get(
                    id=team_booking_id
                )
                
                # Generate the enhanced title and description
                if team_booking.work_item:
                    enhanced_title = f"[{team_booking.work_item.title}] {team_booking.title}"
                    enhanced_description = f"Work Item: {team_booking.work_item.title}\nWorkflow: {team_booking.work_item.workflow.name}\n\n{team_booking.description}"
                else:
                    enhanced_title = team_booking.title
                    enhanced_description = team_booking.description
                
                # Check if update is needed
                if booking_request.title != enhanced_title or booking_request.description != enhanced_description:
                    self.stdout.write(f'Updating booking {booking_request.id}:')
                    self.stdout.write(f'  Old title: {booking_request.title}')
                    self.stdout.write(f'  New title: {enhanced_title}')
                    
                    if not dry_run:
                        with transaction.atomic():
                            booking_request.title = enhanced_title
                            booking_request.description = enhanced_description
                            booking_request.save(update_fields=['title', 'description'])
                    
                    updated_count += 1
                else:
                    self.stdout.write(f'Booking {booking_request.id} already up to date')
                
            except TeamBooking.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'No TeamBooking found for BookingRequest {booking_request.id} (source_object_id: {booking_request.source_object_id})')
                )
                error_count += 1
            except ValueError:
                self.stdout.write(
                    self.style.WARNING(f'Invalid source_object_id for BookingRequest {booking_request.id}: {booking_request.source_object_id}')
                )
                error_count += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error updating BookingRequest {booking_request.id}: {str(e)}')
                )
                error_count += 1
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'DRY RUN: Would update {updated_count} bookings')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully updated {updated_count} bookings')
            )
        
        if error_count > 0:
            self.stdout.write(
                self.style.WARNING(f'Encountered {error_count} errors')
            )
