"""
Integration service for connecting scheduling bookings with CFlows work items
"""
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.models import User
from services.cflows.models import WorkItem, WorkflowStep, WorkItemHistory
from services.scheduling.models import BookingRequest
from core.models import UserProfile
import logging

logger = logging.getLogger(__name__)


class BookingWorkflowIntegration:
    """Service to handle workflow updates when bookings are completed"""
    
    @staticmethod
    def get_linked_work_item(booking: BookingRequest) -> WorkItem:
        """
        Get the CFlows work item linked to this booking
        """
        # Case 1: Direct linkage to a work item (legacy / planned design)
        if booking.source_service == 'cflows' and booking.source_object_type == 'work_item':
            try:
                return WorkItem.objects.get(
                    uuid=booking.source_object_id,
                    workflow__organization=booking.organization
                )
            except WorkItem.DoesNotExist:
                logger.warning(f"Work item {booking.source_object_id} not found for booking {booking.uuid}")
                return None

        # Case 2: Booking was created from a TeamBooking (current integration path)
        if booking.source_service == 'cflows' and booking.source_object_type == 'TeamBooking':
            from services.cflows.models import TeamBooking as CflowsTeamBooking
            try:
                team_booking = CflowsTeamBooking.objects.select_related('work_item').get(id=booking.source_object_id)
                return team_booking.work_item
            except CflowsTeamBooking.DoesNotExist:
                logger.warning(
                    f"TeamBooking {booking.source_object_id} not found for booking {booking.uuid}"
                )
                return None

        # Case 3: work_item_id stored in custom_data (fallback / external import)
        if booking.custom_data and booking.custom_data.get('work_item_id'):
            try:
                return WorkItem.objects.get(
                    id=booking.custom_data.get('work_item_id'),
                    workflow__organization=booking.organization
                )
            except WorkItem.DoesNotExist:
                logger.info(
                    f"Custom data work_item_id {booking.custom_data.get('work_item_id')} not found for booking {booking.uuid}"
                )
                return None
        return None
    
    @staticmethod
    def get_completion_options(work_item: WorkItem) -> dict:
        """
        Get available options when a work item's booking is completed
        Returns dict with next steps and completion options
        """
        if not work_item:
            return {}
            
        current_step = work_item.current_step
        workflow = work_item.workflow
        
        # Get available next steps (transitions from current step)
        next_steps = WorkflowStep.objects.filter(
            workflow=workflow,
            incoming_transitions__from_step=current_step,
            incoming_transitions__is_active=True
        ).order_by('order')
        
        # Get backward steps if allowed
        backward_steps = work_item.get_available_backward_steps()
        
        return {
            'work_item': work_item,
            'current_step': current_step,
            'next_steps': [
                {
                    'id': step.id,
                    'name': step.name,
                    'description': step.description,
                    'is_terminal': step.is_terminal,
                    'requires_booking': step.requires_booking,
                    'estimated_duration_hours': step.estimated_duration_hours
                }
                for step in next_steps
            ],
            'backward_steps': [
                {
                    'id': step.id,
                    'name': step.name,
                    'description': step.description
                }
                for step in backward_steps[:3]  # Limit to last 3 steps
            ],
            'can_complete': current_step.is_terminal,
            'requires_booking': current_step.requires_booking
        }
    
    @staticmethod
    @transaction.atomic
    def complete_booking_with_workflow_update(
        booking: BookingRequest, 
        completed_by: UserProfile,
        workflow_action: str,
        target_step_id: int = None,
        completion_notes: str = "",
        mark_work_item_complete: bool = False
    ) -> dict:
        """
        Complete a booking and update the linked work item workflow
        
        Args:
            booking: The BookingRequest to complete
            completed_by: UserProfile of the person completing the booking
            workflow_action: 'move_next', 'move_back', 'complete', or 'no_change'
            target_step_id: ID of the step to move to (if workflow_action is move_next/move_back)
            completion_notes: Notes about the completion
            mark_work_item_complete: Whether to mark the work item as completed
            
        Returns:
            dict with success status and messages
        """
        try:
            # Complete the booking
            booking.status = 'completed'
            booking.completed_by = completed_by
            booking.completed_at = timezone.now()
            booking.actual_end = timezone.now()
            
            # Add completion notes to custom data
            if completion_notes:
                booking.custom_data['completion_notes'] = completion_notes
                booking.custom_data['completed_at'] = booking.completed_at.isoformat()
            
            booking.save()
            
            result = {
                'success': True,
                'booking_completed': True,
                'messages': ['Booking completed successfully.']
            }
            
            # Handle work item updates if linked
            work_item = BookingWorkflowIntegration.get_linked_work_item(booking)
            if work_item and workflow_action != 'no_change':
                
                if workflow_action == 'complete' or mark_work_item_complete:
                    # Mark work item as completed
                    work_item.is_completed = True
                    work_item.completed_at = timezone.now()
                    work_item.current_assignee = completed_by
                    work_item.save()
                    
                    # Add history entry
                    WorkItemHistory.objects.create(
                        work_item=work_item,
                        changed_by=completed_by,
                        field_name='status',
                        old_value='in_progress',
                        new_value='completed',
                        notes=f"Completed via booking completion. {completion_notes}".strip()
                    )
                    
                    result['messages'].append('Work item marked as completed.')
                    result['work_item_completed'] = True
                    
                elif workflow_action in ['move_next', 'move_back'] and target_step_id:
                    # Move work item to different step
                    try:
                        target_step = WorkflowStep.objects.get(
                            id=target_step_id,
                            workflow=work_item.workflow
                        )
                        
                        old_step = work_item.current_step
                        work_item.current_step = target_step
                        work_item.updated_at = timezone.now()
                        
                        # Update assignee if step has default assignee
                        if hasattr(target_step, 'default_assignee') and target_step.default_assignee:
                            work_item.current_assignee = target_step.default_assignee
                        
                        work_item.save()
                        
                        # Add history entry
                        WorkItemHistory.objects.create(
                            work_item=work_item,
                            changed_by=completed_by,
                            field_name='workflow_step',
                            old_value=old_step.name,
                            new_value=target_step.name,
                            notes=f"Moved via booking completion: {booking.title}. {completion_notes}".strip()
                        )
                        
                        result['messages'].append(f'Work item moved to "{target_step.name}".')
                        result['work_item_moved'] = True
                        result['new_step'] = target_step.name
                        
                        # Check if the new step is final
                        if target_step.is_terminal:
                            work_item.is_completed = True
                            work_item.completed_at = timezone.now()
                            work_item.save()
                            result['messages'].append('Work item automatically completed (final step).')
                            result['work_item_completed'] = True
                            
                    except WorkflowStep.DoesNotExist:
                        result['messages'].append('Warning: Selected workflow step not found.')
                        logger.error(f"WorkflowStep {target_step_id} not found for work_item {work_item.uuid}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error completing booking with workflow update: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'messages': ['An error occurred while completing the booking.']
            }
    
    @staticmethod
    def should_prompt_workflow_update(booking: BookingRequest) -> bool:
        """
        Determine if user should be prompted for workflow update when completing booking
        """
        if booking.status == 'completed':
            return False
            
        work_item = BookingWorkflowIntegration.get_linked_work_item(booking)
        if not work_item:
            return False
            
        # Don't prompt if work item is already completed
        if work_item.is_completed:
            return False
            
        # Check if there are available next steps or if current step can be completed
        completion_options = BookingWorkflowIntegration.get_completion_options(work_item)
        return len(completion_options.get('next_steps', [])) > 0 or completion_options.get('can_complete', False)
