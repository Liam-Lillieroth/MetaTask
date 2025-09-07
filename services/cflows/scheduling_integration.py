"""
Integration service to sync CFlows team bookings with the scheduling service
"""

from django.db import transaction
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

from services.scheduling.models import BookingRequest, SchedulableResource
from .models import TeamBooking
from core.models import Organization, Team


class CFlowsSchedulingIntegration:
    """Service to integrate CFlows team bookings with the scheduling service"""
    
    @staticmethod
    def create_scheduling_booking(team_booking):
        """Create a corresponding BookingRequest in the scheduling service"""
        try:
            with transaction.atomic():
                # Try to find or create a schedulable resource for the team
                # First check if there's already a resource linked to this team
                resource = SchedulableResource.objects.filter(
                    linked_team=team_booking.team,
                    organization=team_booking.team.organization
                ).first()
                
                if not resource:
                    # Try to find by name if no linked resource exists
                    resource = SchedulableResource.objects.filter(
                        organization=team_booking.team.organization,
                        name=f"Team: {team_booking.team.name}"
                    ).first()
                    
                    if not resource:
                        # Create new resource
                        resource = SchedulableResource.objects.create(
                            organization=team_booking.team.organization,
                            name=f"Team: {team_booking.team.name}",
                            resource_type='team',
                            description=f'Team resource for {team_booking.team.name}',
                            max_concurrent_bookings=team_booking.team.members.count() or 5,
                            is_active=True,
                            service_type='cflows'
                        )
                        
                        # Try to link the team if no other resource is linked to it
                        if not SchedulableResource.objects.filter(linked_team=team_booking.team).exists():
                            resource.linked_team = team_booking.team
                            resource.save()
                
                # Enhance title and description with work item context
                enhanced_title = team_booking.title
                enhanced_description = team_booking.description
                
                if team_booking.work_item:
                    # Include work item title in the booking title for better visibility
                    enhanced_title = f"{team_booking.work_item.title} - {team_booking.title}"
                    
                    # Add work item context to description
                    work_item_info = f"Work Item: {team_booking.work_item.title}\n"
                    if team_booking.workflow_step:
                        work_item_info += f"Workflow Step: {team_booking.workflow_step.name}\n"
                    work_item_info += f"Original Booking: {team_booking.title}\n"
                    if team_booking.description:
                        work_item_info += f"\n{team_booking.description}"
                    enhanced_description = work_item_info
                
                # Create the booking request
                booking_request = BookingRequest.objects.create(
                    organization=team_booking.team.organization,
                    title=enhanced_title,
                    description=enhanced_description,
                    requested_start=team_booking.start_time,
                    requested_end=team_booking.end_time,
                    resource=resource,
                    required_capacity=team_booking.required_members,
                    status='confirmed',  # CFlows bookings are automatically confirmed
                    priority='normal',
                    source_service='cflows',
                    source_object_type='TeamBooking',
                    source_object_id=str(team_booking.id),
                    requested_by=team_booking.booked_by,
                    custom_data={
                        'work_item_id': team_booking.work_item.id if team_booking.work_item else None,
                        'work_item_title': team_booking.work_item.title if team_booking.work_item else None,
                        'workflow_step_id': team_booking.workflow_step.id if team_booking.workflow_step else None,
                        'workflow_step_name': team_booking.workflow_step.name if team_booking.workflow_step else None,
                        'team_id': team_booking.team.id,
                        'team_name': team_booking.team.name,
                        'job_type_id': team_booking.job_type.id if team_booking.job_type else None,
                        'original_booking_title': team_booking.title,
                    }
                )
                
                # If team booking is completed, mark scheduling booking as completed too
                if team_booking.is_completed:
                    booking_request.status = 'completed'
                    booking_request.completed_at = team_booking.completed_at
                    booking_request.completed_by = team_booking.completed_by
                    booking_request.actual_start = team_booking.start_time
                    booking_request.actual_end = team_booking.end_time
                    booking_request.save()
                
                return booking_request
                
        except Exception as e:
            print(f"Error creating scheduling booking for team booking {team_booking.id}: {str(e)}")
            return None
    
    @staticmethod
    def update_scheduling_booking(team_booking):
        """Update the corresponding BookingRequest when TeamBooking is updated"""
        try:
            booking_request = BookingRequest.objects.get(
                source_service='cflows',
                source_object_type='TeamBooking',
                source_object_id=str(team_booking.id)
            )
            
            # Enhance title and description with work item context (same as create)
            enhanced_title = team_booking.title
            enhanced_description = team_booking.description
            
            if team_booking.work_item:
                # Include work item title in the booking title for better visibility
                enhanced_title = f"{team_booking.work_item.title} - {team_booking.title}"
                
                # Add work item context to description
                work_item_info = f"Work Item: {team_booking.work_item.title}\n"
                if team_booking.workflow_step:
                    work_item_info += f"Workflow Step: {team_booking.workflow_step.name}\n"
                work_item_info += f"Original Booking: {team_booking.title}\n"
                if team_booking.description:
                    work_item_info += f"\n{team_booking.description}"
                enhanced_description = work_item_info
            
            # Update the booking request fields
            booking_request.title = enhanced_title
            booking_request.description = enhanced_description
            booking_request.requested_start = team_booking.start_time
            booking_request.requested_end = team_booking.end_time
            booking_request.required_capacity = team_booking.required_members
            
            # Update custom data with enhanced context
            booking_request.custom_data = {
                'work_item_id': team_booking.work_item.id if team_booking.work_item else None,
                'work_item_title': team_booking.work_item.title if team_booking.work_item else None,
                'workflow_step_id': team_booking.workflow_step.id if team_booking.workflow_step else None,
                'workflow_step_name': team_booking.workflow_step.name if team_booking.workflow_step else None,
                'team_id': team_booking.team.id,
                'team_name': team_booking.team.name,
                'job_type_id': team_booking.job_type.id if team_booking.job_type else None,
                'original_booking_title': team_booking.title,
            }
            
            # Update completion status
            if team_booking.is_completed and booking_request.status != 'completed':
                booking_request.status = 'completed'
                booking_request.completed_at = team_booking.completed_at
                booking_request.completed_by = team_booking.completed_by
                booking_request.actual_start = team_booking.start_time
                booking_request.actual_end = team_booking.end_time
            elif not team_booking.is_completed and booking_request.status == 'completed':
                booking_request.status = 'confirmed'
                booking_request.completed_at = None
                booking_request.completed_by = None
                booking_request.actual_start = None
                booking_request.actual_end = None
            
            booking_request.save()
            return booking_request
            
        except BookingRequest.DoesNotExist:
            # If no corresponding booking request exists, create one
            return CFlowsSchedulingIntegration.create_scheduling_booking(team_booking)
        except Exception as e:
            print(f"Error updating scheduling booking for team booking {team_booking.id}: {str(e)}")
            return None
    
    @staticmethod
    def delete_scheduling_booking(team_booking):
        """Delete the corresponding BookingRequest when TeamBooking is deleted"""
        try:
            booking_request = BookingRequest.objects.get(
                source_service='cflows',
                source_object_type='TeamBooking',
                source_object_id=str(team_booking.id)
            )
            booking_request.delete()
            return True
            
        except BookingRequest.DoesNotExist:
            # Already deleted or never existed
            return True
        except Exception as e:
            print(f"Error deleting scheduling booking for team booking {team_booking.id}: {str(e)}")
            return False
    
    @staticmethod
    def sync_existing_bookings(organization=None):
        """Sync all existing CFlows team bookings with scheduling service"""
        if organization:
            team_bookings = TeamBooking.objects.filter(team__organization=organization)
        else:
            team_bookings = TeamBooking.objects.all()
        
        synced_count = 0
        error_count = 0
        
        for team_booking in team_bookings:
            # Check if booking already exists in scheduling
            existing_booking = BookingRequest.objects.filter(
                source_service='cflows',
                source_object_type='TeamBooking',
                source_object_id=str(team_booking.id)
            ).first()
            
            if not existing_booking:
                result = CFlowsSchedulingIntegration.create_scheduling_booking(team_booking)
                if result:
                    synced_count += 1
                else:
                    error_count += 1
            else:
                result = CFlowsSchedulingIntegration.update_scheduling_booking(team_booking)
                if result:
                    synced_count += 1
                else:
                    error_count += 1
        
        return synced_count, error_count
    
    @staticmethod
    def get_linked_work_item_for_booking(booking_request):
        """Get the CFlows work item linked to a scheduling booking"""
        if (booking_request.source_service == 'cflows' and 
            booking_request.source_object_type == 'TeamBooking'):
            try:
                team_booking = TeamBooking.objects.get(id=booking_request.source_object_id)
                return team_booking.work_item
            except TeamBooking.DoesNotExist:
                return None
        return None
    
    @staticmethod
    def handle_scheduling_booking_completion(booking_request):
        """Handle completion of scheduling booking - mark corresponding CFlows TeamBooking as complete"""
        from .models import TeamBooking, WorkflowStep
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            # Find the corresponding TeamBooking
            team_booking = TeamBooking.objects.get(id=booking_request.source_object_id)
            
            # Mark the team booking as complete
            team_booking.is_completed = True
            team_booking.completed_at = timezone.now()
            
            # Add completion notes if provided (create a WorkItem comment)
            completion_notes = booking_request.custom_data.get('completion_notes', '')
            if completion_notes and team_booking.work_item:
                from .models import WorkItemComment
                WorkItemComment.objects.create(
                    work_item=team_booking.work_item,
                    author=None,  # System comment
                    content=f"Booking completion notes: {completion_notes}",
                    is_system_comment=True
                )
            
            team_booking.save()
            
            # Try to advance the work item workflow if this is the final booking
            work_item = team_booking.work_item
            if work_item and work_item.workflow_step:
                current_step = work_item.workflow_step
                
                # Check if all team bookings for this work item are complete
                all_bookings = TeamBooking.objects.filter(work_item=work_item)
                incomplete_bookings = all_bookings.filter(is_completed=False)
                
                if not incomplete_bookings.exists():
                    # All bookings are complete, try to advance workflow
                    # Find a transition that doesn't require approval
                    from .models import WorkflowTransition
                    transitions = WorkflowTransition.objects.filter(
                        from_step=current_step,
                        requires_booking=False  # Auto-advance transitions
                    ).first()
                    
                    if transitions and transitions.to_step.is_terminal:
                        work_item.current_step = transitions.to_step
                        work_item.is_completed = True
                        work_item.completed_at = timezone.now()
                        work_item.save()
                        
                        logger.info(f"Work item {work_item.id} automatically completed after all bookings finished")
            
            logger.info(f"TeamBooking {team_booking.id} marked as complete from scheduling service")
            return True
            
        except TeamBooking.DoesNotExist:
            logger.error(f"TeamBooking with id {booking_request.source_object_id} not found")
            return False
        except Exception as e:
            logger.error(f"Error handling scheduling booking completion: {str(e)}")
            return False

    @staticmethod
    def sync_completed_bookings_retroactively(organization=None):
        """
        Sync already completed scheduling bookings with CFlows team bookings
        This handles cases where bookings were completed before bidirectional sync was implemented
        """
        from services.scheduling.models import BookingRequest
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Find completed scheduling bookings that originated from CFlows
        completed_bookings = BookingRequest.objects.filter(
            source_service='cflows',
            source_object_type='TeamBooking',
            status='completed'  # Note: using 'completed' not 'complete'
        )
        
        if organization:
            completed_bookings = completed_bookings.filter(organization=organization)
        
        synced_count = 0
        error_count = 0
        
        for booking in completed_bookings:
            try:
                team_booking = TeamBooking.objects.get(id=booking.source_object_id)
                
                # Skip if already completed
                if team_booking.is_completed:
                    continue
                
                # Use the existing handler method
                result = CFlowsSchedulingIntegration.handle_scheduling_booking_completion(booking)
                if result:
                    synced_count += 1
                else:
                    error_count += 1
                    
            except TeamBooking.DoesNotExist:
                logger.error(f"TeamBooking {booking.source_object_id} not found for booking {booking.id}")
                error_count += 1
            except Exception as e:
                logger.error(f"Error syncing completed booking {booking.id}: {str(e)}")
                error_count += 1
        
        logger.info(f"Retroactive sync completed: {synced_count} synced, {error_count} errors")
        return synced_count, error_count
