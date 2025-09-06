from django.utils import timezone
from datetime import datetime, timedelta
from typing import Dict, List, Any
from .models import SchedulableResource, BookingRequest
from .services import SchedulingService


class ServiceIntegration:
    """Base class for service integrations"""
    
    def __init__(self, organization):
        self.organization = organization
        self.scheduling_service = SchedulingService(organization)

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
        description: str = '',
        priority: str = 'normal',
        custom_data: Dict[str, Any] = None
    ) -> BookingRequest:
        """Create a generic booking request"""
        
        try:
            resource = SchedulableResource.objects.get(
                organization=self.organization,
                name=resource_name,
                is_active=True
            )
        except SchedulableResource.DoesNotExist:
            raise ValueError(f"Resource '{resource_name}' not found")
        
        from core.models import UserProfile
        requested_by = UserProfile.objects.get(id=requested_by_id)
        
        booking = BookingRequest.objects.create(
            organization=self.organization,
            title=title,
            description=description,
            requested_start=start_time,
            requested_end=end_time,
            resource=resource,
            status='pending',
            priority=priority,
            source_service=source_service,
            source_object_type=source_object_type,
            source_object_id=source_object_id,
            requested_by=requested_by,
            custom_data=custom_data or {}
        )
        
        # Check if booking can be auto-confirmed
        if self.scheduling_service.can_auto_confirm(booking):
            self.scheduling_service.confirm_booking(booking)
        
        return booking


class CFlowsIntegration(ServiceIntegration):
    """Integration with CFlows service"""
    
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
        
        if not isinstance(team_booking, TeamBooking):
            raise ValueError("Expected TeamBooking instance")
        
        # Get or create schedulable resource for the team
        resource, created = SchedulableResource.objects.get_or_create(
            organization=self.organization,
            linked_team=team_booking.team,
            defaults={
                'name': team_booking.team.name,
                'resource_type': 'team',
                'description': f"Team resource for {team_booking.team.name}",
                'service_type': 'cflows',
                'max_concurrent_bookings': team_booking.team.default_capacity,
            }
        )
        
        # Check if booking already exists
        existing_booking = BookingRequest.objects.filter(
            source_service='cflows',
            source_object_type='team_booking',
            source_object_id=str(team_booking.id)
        ).first()
        
        custom_data = {
            'team_booking_id': team_booking.id,
            'work_item_id': team_booking.work_item.id if team_booking.work_item else None,
            'workflow_step_id': team_booking.workflow_step.id if team_booking.workflow_step else None,
            'job_type_id': team_booking.job_type.id if team_booking.job_type else None,
            'required_members': team_booking.required_members,
            'is_completed': team_booking.is_completed
        }
        
        if existing_booking:
            # Update existing booking
            existing_booking.title = team_booking.title
            existing_booking.description = team_booking.description
            existing_booking.requested_start = team_booking.start_time
            existing_booking.requested_end = team_booking.end_time
            existing_booking.required_capacity = team_booking.required_members
            existing_booking.custom_data = custom_data
            
            # Update status based on TeamBooking state
            if team_booking.is_completed:
                existing_booking.status = 'completed'
                existing_booking.actual_end = team_booking.completed_at
                existing_booking.completed_by = team_booking.completed_by
            
            existing_booking.save()
            return existing_booking
        else:
            # Create new booking
            status = 'completed' if team_booking.is_completed else 'confirmed'
            
            booking = BookingRequest.objects.create(
                organization=self.organization,
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
                custom_data=custom_data
            )
            
            if team_booking.is_completed:
                booking.actual_end = team_booking.completed_at
                booking.completed_by = team_booking.completed_by
                booking.save()
            
            # Add assigned members
            if team_booking.assigned_members.exists():
                booking.assigned_to.set(team_booking.assigned_members.all())
            
            return booking

    def sync_all_team_bookings(self) -> List[BookingRequest]:
        """Sync all existing TeamBookings to new scheduling system"""
        
        from services.cflows.models import TeamBooking
        
        team_bookings = TeamBooking.objects.filter(
            team__organization=self.organization
        ).select_related('team', 'work_item', 'workflow_step', 'job_type', 'booked_by', 'completed_by')
        
        synced_bookings = []
        for team_booking in team_bookings:
            try:
                booking = self.update_from_team_booking(team_booking)
                synced_bookings.append(booking)
            except Exception as e:
                # Log error but continue with other bookings
                print(f"Error syncing TeamBooking {team_booking.id}: {e}")
                continue
        
        return synced_bookings

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

    def get_team_schedule(
        self,
        team_name: str,
        start_datetime: datetime,
        end_datetime: datetime
    ) -> List[Dict[str, Any]]:
        """Get schedule for a specific team"""
        try:
            resource = SchedulableResource.objects.get(
                organization=self.organization,
                name=team_name,
                resource_type='team',
                is_active=True
            )
            
            return self.scheduling_service.get_resource_schedule(
                resource, start_datetime, end_datetime
            )
        except SchedulableResource.DoesNotExist:
            return []

    def get_team_availability(
        self,
        team_name: str,
        start_date,
        end_date
    ) -> Dict[str, Any]:
        """Get availability information for a team"""
        try:
            resource = SchedulableResource.objects.get(
                organization=self.organization,
                name=team_name,
                resource_type='team',
                is_active=True
            )
            
            return self.scheduling_service.get_resource_availability(
                resource, start_date, end_date
            )
        except SchedulableResource.DoesNotExist:
            return {}

    def complete_work_item_booking(self, work_item_id: int, completed_by) -> bool:
        """Mark all bookings for a work item as completed"""
        
        bookings = BookingRequest.objects.filter(
            source_service='cflows',
            source_object_type='work_item',
            source_object_id=str(work_item_id),
            status__in=['confirmed', 'in_progress']
        )
        
        success = True
        for booking in bookings:
            if not self.scheduling_service.complete_booking(booking, completed_by):
                success = False
        
        return success

    def cancel_work_item_booking(self, work_item_id: int, cancelled_by) -> bool:
        """Cancel all bookings for a work item"""
        
        bookings = BookingRequest.objects.filter(
            source_service='cflows',
            source_object_type='work_item',
            source_object_id=str(work_item_id),
            status__in=['pending', 'confirmed', 'in_progress']
        )
        
        success = True
        for booking in bookings:
            if not self.scheduling_service.cancel_booking(booking, cancelled_by):
                success = False
        
        return success


def get_service_integration(organization, service_name: str) -> ServiceIntegration:
    """Factory function to get appropriate service integration"""
    if service_name == 'cflows':
        return CFlowsIntegration(organization)
    else:
        return ServiceIntegration(organization)