from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from django.utils import timezone
from .models import BookingRequest, SchedulableResource
from .services import SchedulingService


class ServiceIntegration(ABC):
    """Abstract base class for service integrations"""
    
    def __init__(self, organization):
        self.organization = organization
        self.scheduling_service = SchedulingService(organization)
    
    @abstractmethod
    def sync_data(self):
        """Abstract method for data synchronization"""
        pass
    
    def handle_booking_created(self, booking: BookingRequest):
        """Hook for new bookings - can be overridden by subclasses"""
        pass
    
    def handle_booking_cancelled(self, booking: BookingRequest):
        """Hook for cancellations - can be overridden by subclasses"""
        pass
    
    def get_booking_by_source(
        self,
        source_service: str,
        source_object_type: str,
        source_object_id: str
    ) -> Optional[BookingRequest]:
        """Get booking by source information"""
        try:
            return BookingRequest.objects.get(
                organization=self.organization,
                source_service=source_service,
                source_object_type=source_object_type,
                source_object_id=source_object_id
            )
        except BookingRequest.DoesNotExist:
            return None
    
    def create_booking_request(
        self,
        title: str,
        resource_name: str,
        start_time: datetime,
        end_time: datetime,
        source_service: str,
        source_object_type: str,
        source_object_id: str,
        requested_by_id: int,
        description: str = "",
        priority: str = "normal",
        custom_data: Dict[str, Any] = None
    ) -> BookingRequest:
        """Create a booking request from any service"""
        
        try:
            resource = SchedulableResource.objects.get(
                organization=self.organization,
                name=resource_name,
                is_active=True
            )
        except SchedulableResource.DoesNotExist:
            raise ValueError(f"Resource '{resource_name}' not found")
        
        booking = BookingRequest.objects.create(
            organization=self.organization,
            title=title,
            description=description,
            requested_start=start_time,
            requested_end=end_time,
            resource=resource,
            source_service=source_service,
            source_object_type=source_object_type,
            source_object_id=source_object_id,
            requested_by_id=requested_by_id,
            priority=priority,
            custom_data=custom_data or {}
        )
        
        # Auto-confirm if resource allows it
        if self.scheduling_service.can_auto_confirm(booking):
            self.scheduling_service.confirm_booking(booking)
        
        return booking

    def get_booking_by_source(
        self,
        source_service: str,
        source_object_type: str,
        source_object_id: str
    ) -> Optional[BookingRequest]:
        """Get booking by source service information"""
        try:
            return BookingRequest.objects.get(
                organization=self.organization,
                source_service=source_service,
                source_object_type=source_object_type,
                source_object_id=source_object_id
            )
        except BookingRequest.DoesNotExist:
            return None
    
    def update_booking_status(
        self,
        source_service: str,
        source_object_type: str,
        source_object_id: str,
        new_status: str
    ) -> bool:
        """Update booking status from source service"""
        booking = self.get_booking_by_source(source_service, source_object_type, source_object_id)
        if booking:
            booking.status = new_status
            if new_status == 'completed':
                booking.completed_at = timezone.now()
            booking.save()
            return True
        return False


class CFlowsIntegration(ServiceIntegration):
    """Integration with CFlows service"""
    
    def sync_data(self):
        """Synchronize TeamBookings with scheduling system"""
        return self.sync_all_team_bookings()
    
    def create_work_item_booking(
        self,
        work_item,
        workflow_step,
        requested_by,
        start_time: datetime,
        duration_hours: float = 2.0,
        custom_data: Dict[str, Any] = None
    ) -> BookingRequest:
        """Create booking from CFlows work item"""
        
        if not workflow_step.assigned_team:
            raise ValueError("Workflow step must have assigned team")
        
        # Get or create schedulable resource for the team
        resource, created = SchedulableResource.objects.get_or_create(
            organization=self.organization,
            linked_team=workflow_step.assigned_team,
            defaults={
                'name': workflow_step.assigned_team.name,
                'resource_type': 'team',
                'description': f"Team resource for {workflow_step.assigned_team.name}",
                'service_type': 'cflows',
                'max_concurrent_bookings': workflow_step.assigned_team.default_capacity,
            }
        )
        
        end_time = start_time + timedelta(hours=duration_hours)
        
        booking_data = {
            'work_item_id': work_item.id,
            'workflow_step_id': workflow_step.id,
            'estimated_duration': duration_hours,
            'team_id': workflow_step.assigned_team.id
        }
        if custom_data:
            booking_data.update(custom_data)
        
        return self.create_booking_request(
            title=f"{work_item.title} - {workflow_step.name}",
            resource_name=resource.name,
            start_time=start_time,
            end_time=end_time,
            source_service='cflows',
            source_object_type='work_item',
            source_object_id=str(work_item.id),
            requested_by_id=requested_by.id,
            description=f"Booking for work item: {work_item.title}",
            priority=work_item.priority if hasattr(work_item, 'priority') else 'normal',
            custom_data=booking_data
        )
    
    def update_from_team_booking(self, team_booking) -> BookingRequest:
        """Create or update booking from existing TeamBooking"""
        from services.cflows.models import TeamBooking
        
        # Check if booking already exists
        existing_booking = self.get_booking_by_source(
            'cflows', 'team_booking', str(team_booking.id)
        )
        
        if existing_booking:
            # Update existing booking
            existing_booking.title = team_booking.title
            existing_booking.description = team_booking.description
            existing_booking.requested_start = team_booking.start_time
            existing_booking.requested_end = team_booking.end_time
            existing_booking.status = 'completed' if team_booking.is_completed else 'confirmed'
            if team_booking.is_completed:
                existing_booking.completed_at = team_booking.completed_at
                existing_booking.completed_by = team_booking.completed_by
            existing_booking.save()
            return existing_booking
        
        # Get or create resource for team
        resource, created = SchedulableResource.objects.get_or_create(
            organization=team_booking.team.organization,
            linked_team=team_booking.team,
            defaults={
                'name': team_booking.team.name,
                'resource_type': 'team',
                'service_type': 'cflows',
                'max_concurrent_bookings': team_booking.team.default_capacity,
            }
        )
        
        status = 'completed' if team_booking.is_completed else 'confirmed'
        
        booking = BookingRequest.objects.create(
            organization=team_booking.team.organization,
            title=team_booking.title,
            description=team_booking.description,
            requested_start=team_booking.start_time,
            requested_end=team_booking.end_time,
            resource=resource,
            required_capacity=team_booking.required_members,
            status=status,
            source_service='cflows',
            source_object_type='team_booking',
            source_object_id=str(team_booking.id),
            requested_by=team_booking.booked_by,
            completed_by=team_booking.completed_by,
            completed_at=team_booking.completed_at,
            custom_data={
                'legacy_team_booking_id': team_booking.id,
                'work_item_id': team_booking.work_item.id if team_booking.work_item else None,
                'workflow_step_id': team_booking.workflow_step.id if team_booking.workflow_step else None,
                'required_members': team_booking.required_members,
            }
        )
        
        # Assign team members if any
        if hasattr(team_booking, 'assigned_members'):
            booking.assigned_to.set(team_booking.assigned_members.all())
        
        return booking
    
    def sync_all_team_bookings(self) -> List[BookingRequest]:
        """Sync all existing TeamBookings to new scheduling system"""
        from services.cflows.models import TeamBooking
        
        bookings_created = []
        team_bookings = TeamBooking.objects.filter(
            team__organization=self.organization
        ).select_related('team', 'work_item', 'workflow_step', 'booked_by', 'completed_by')
        
        for team_booking in team_bookings:
            try:
                booking = self.update_from_team_booking(team_booking)
                bookings_created.append(booking)
            except Exception as e:
                # Log error but continue processing
                print(f"Error syncing TeamBooking {team_booking.id}: {e}")
        
        return bookings_created
    
    def suggest_booking_times(
        self,
        team_name: str,
        preferred_start: datetime,
        duration_hours: float,
        max_alternatives: int = 5
    ) -> List[Dict[str, Any]]:
        """Suggest available booking times for a team"""
        try:
            resource = SchedulableResource.objects.get(
                organization=self.organization,
                name=team_name,
                resource_type='team',
                is_active=True
            )
            
            duration = timedelta(hours=duration_hours)
            return self.scheduling_service.suggest_alternative_times(
                resource, preferred_start, duration, max_alternatives
            )
        except SchedulableResource.DoesNotExist:
            return []
    
    def mark_completed(self, request, queryset):
        from django.utils import timezone
        from services.cflows.models import TeamBooking

        # Handle both QuerySet and list inputs
        if isinstance(queryset, list):
            bookings = queryset
            # Update individual bookings
            for booking in bookings:
                if booking.status in ['confirmed', 'in_progress']:
                    booking.status = 'completed'
                    booking.completed_at = timezone.now()
                    booking.save()
        else:
            # Handle QuerySet
            updates = queryset.filter(status__in=['confirmed', 'in_progress']).update(
                status='completed',
                completed_at=timezone.now()
            )
            bookings = list(queryset)

        for booking in bookings:
            if (booking.source_service == 'cflows' and 
                booking.source_object_type.lower() in ['teambooking', 'team_booking']):
                try:
                    team_booking = TeamBooking.objects.get(id=booking.source_object_id)
                    team_booking.is_completed = True
                    team_booking.completed_at = timezone.now()
                    team_booking.completed_by = request.user.userprofile if hasattr(request.user, 'userprofile') else None
                    team_booking.save()
                except TeamBooking.DoesNotExist:
                    pass
        
        # Only message_user if we have a proper admin request (not called from view)
        if hasattr(self, 'message_user') and hasattr(request, 'META'):
            self.message_user(request, f'{len(bookings)} bookings marked as completed.')

class DefaultIntegration(ServiceIntegration):
    """Default integration implementation for unknown services"""
    
    def sync_data(self):
        """Default sync does nothing"""
        return []


def get_service_integration(organization, service_name: str) -> ServiceIntegration:
    """Factory function to get appropriate service integration"""
    if service_name == 'cflows':
        return CFlowsIntegration(organization)
    else:
        return DefaultIntegration(organization)
