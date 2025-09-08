from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, time, date
from django.utils import timezone
from django.db.models import Q, Sum, Count, F
from django.core.exceptions import ValidationError
from .models import BookingRequest, SchedulableResource, ResourceScheduleRule


class SchedulingService:
    """Core scheduling business logic"""
    
    def __init__(self, organization):
        self.organization = organization
    
    def check_availability(
        self,
        resource: SchedulableResource,
        start_time: datetime,
        end_time: datetime,
        exclude_booking_id: Optional[int] = None
    ) -> bool:
        """Validates time slot availability"""
        return self.is_time_slot_available(resource, start_time, end_time, exclude_booking_id)
    
    def create_booking(
        self,
        user_profile,
        resource: SchedulableResource,
        start_time: datetime,
        end_time: datetime,
        **kwargs
    ) -> BookingRequest:
        """Creates new booking"""
        
        # Validate time slot is available
        if not self.is_time_slot_available(resource, start_time, end_time):
            raise ValidationError("Time slot is not available")
        
        # Extract optional parameters
        title = kwargs.get('title', f'Booking for {resource.name}')
        description = kwargs.get('description', '')
        priority = kwargs.get('priority', 'normal')
        source_service = kwargs.get('source_service', 'scheduling')
        source_object_type = kwargs.get('source_object_type', 'booking')
        source_object_id = kwargs.get('source_object_id', '')
        custom_data = kwargs.get('custom_data', {})
        
        booking = BookingRequest.objects.create(
            organization=self.organization,
            title=title,
            description=description,
            requested_start=start_time,
            requested_end=end_time,
            resource=resource,
            requested_by=user_profile,
            priority=priority,
            source_service=source_service,
            source_object_type=source_object_type,
            source_object_id=source_object_id,
            custom_data=custom_data,
            status='pending'
        )
        
        # Auto-confirm if allowed
        if self.can_auto_confirm(booking):
            booking.status = 'confirmed'
            booking.save()
        
        return booking
    
    def approve_booking(self, booking_id: int, approver) -> bool:
        """Approves pending booking"""
        try:
            booking = BookingRequest.objects.get(
                id=booking_id,
                organization=self.organization,
                status='pending'
            )
            return self.confirm_booking(booking, approver)
        except BookingRequest.DoesNotExist:
            return False
    
    def cancel_booking_by_id(self, booking_id: int, user, reason: str = "") -> bool:
        """Cancels existing booking by ID"""
        try:
            booking = BookingRequest.objects.get(
                id=booking_id,
                organization=self.organization
            )
            return self.cancel_booking(booking, reason)
        except BookingRequest.DoesNotExist:
            return False
    
    def get_upcoming_bookings(self, organization=None, days: int = 7) -> List[BookingRequest]:
        """Retrieves upcoming bookings"""
        organization = organization or self.organization
        
        start_time = timezone.now()
        end_time = start_time + timedelta(days=days)
        
        return BookingRequest.objects.filter(
            organization=organization,
            status__in=['confirmed', 'in_progress'],
            requested_start__gte=start_time,
            requested_start__lte=end_time
        ).select_related('resource', 'requested_by').order_by('requested_start')
    
    def get_utilization_stats(
        self,
        resource: SchedulableResource,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Calculates usage statistics"""
        return self.get_resource_utilization_stats(resource, start_date, end_date)
    
    def get_resource_availability(
        self,
        resource: SchedulableResource,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Get detailed availability for a resource"""
        
        bookings = BookingRequest.objects.filter(
            resource=resource,
            status__in=['confirmed', 'in_progress'],
            requested_start__date__gte=start_date,
            requested_end__date__lte=end_date
        ).select_related('requested_by')
        
        # Group by date
        daily_stats = {}
        current_date = start_date
        
        while current_date <= end_date:
            day_bookings = bookings.filter(
                requested_start__date=current_date
            )
            
            total_hours = 0
            booking_count = day_bookings.count()
            
            for booking in day_bookings:
                duration = booking.requested_end - booking.requested_start
                total_hours += duration.total_seconds() / 3600
            
            # Check availability rules
            is_available = self._is_date_available(resource, current_date)
            max_capacity = self._get_daily_capacity(resource, current_date)
            
            daily_stats[current_date.isoformat()] = {
                'date': current_date,
                'is_available': is_available,
                'booking_count': booking_count,
                'total_hours': round(total_hours, 2),
                'max_capacity': max_capacity,
                'utilization_percent': round((total_hours / max_capacity) * 100, 1) if max_capacity > 0 else 0,
                'bookings': list(day_bookings.values(
                    'id', 'uuid', 'title', 'requested_start', 'requested_end', 'status', 'priority'
                ))
            }
            
            current_date += timedelta(days=1)
        
        return daily_stats
    
    def get_resource_schedule(
        self,
        resource: SchedulableResource,
        start_datetime: datetime,
        end_datetime: datetime
    ) -> List[Dict[str, Any]]:
        """Get detailed schedule for a resource in a time range"""
        
        bookings = BookingRequest.objects.filter(
            resource=resource,
            status__in=['confirmed', 'in_progress', 'completed'],
            requested_start__lt=end_datetime,
            requested_end__gt=start_datetime
        ).select_related('requested_by', 'completed_by').order_by('requested_start')
        
        schedule_items = []
        for booking in bookings:
            schedule_items.append({
                'id': booking.id,
                'uuid': str(booking.uuid),
                'title': booking.title,
                'description': booking.description,
                'start': booking.requested_start.isoformat(),
                'end': booking.requested_end.isoformat(),
                'actual_start': booking.actual_start.isoformat() if booking.actual_start else None,
                'actual_end': booking.actual_end.isoformat() if booking.actual_end else None,
                'status': booking.status,
                'priority': booking.priority,
                'source_service': booking.source_service,
                'requested_by': booking.requested_by.user.get_full_name() if booking.requested_by else None,
                'completed_by': booking.completed_by.user.get_full_name() if booking.completed_by else None,
                'custom_data': booking.custom_data,
            })
        
        return schedule_items
    
    def is_time_slot_available(
        self,
        resource: SchedulableResource,
        start_time: datetime,
        end_time: datetime,
        exclude_booking_id: Optional[int] = None
    ) -> bool:
        """Check if a time slot is available for booking"""
        
        # Check for conflicts with existing bookings
        conflicts_query = BookingRequest.objects.filter(
            resource=resource,
            status__in=['confirmed', 'in_progress'],
            requested_start__lt=end_time,
            requested_end__gt=start_time
        )
        
        if exclude_booking_id:
            conflicts_query = conflicts_query.exclude(id=exclude_booking_id)
        
        conflicts = conflicts_query.count()
        
        # Check if we exceed resource capacity
        if conflicts >= resource.max_concurrent_bookings:
            return False
        
        # Check availability rules
        if not self._is_datetime_available(resource, start_time, end_time):
            return False
        
        # Check for blackout periods
        if self._is_blackout_period(resource, start_time, end_time):
            return False
        
        return True
    
    def suggest_alternative_times(
        self,
        resource: SchedulableResource,
        preferred_start: datetime,
        duration: timedelta,
        max_alternatives: int = 5
    ) -> List[Dict[str, Any]]:
        """Suggest alternative booking times if preferred time is unavailable"""
        
        alternatives = []
        
        # Check if preferred time is available
        preferred_end = preferred_start + duration
        if self.is_time_slot_available(resource, preferred_start, preferred_end):
            return [{
                'start_time': preferred_start.isoformat(),
                'end_time': preferred_end.isoformat(),
                'score': 100,
                'reason': 'Preferred time available'
            }]
        
        # Look for alternatives within 5 days
        search_start = preferred_start.replace(hour=8, minute=0, second=0, microsecond=0)
        search_end = search_start + timedelta(days=5)
        
        current_time = search_start
        while current_time < search_end and len(alternatives) < max_alternatives:
            end_time = current_time + duration
            
            if self.is_time_slot_available(resource, current_time, end_time):
                # Calculate score based on proximity to preferred time
                time_diff_hours = abs((current_time - preferred_start).total_seconds()) / 3600
                score = max(0, 100 - time_diff_hours)  # Decrease by 1 point per hour difference
                
                # Bonus for same day
                if current_time.date() == preferred_start.date():
                    score += 10
                
                alternatives.append({
                    'start_time': current_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'score': round(score, 1),
                    'reason': f"Available {time_diff_hours:.1f} hours from preferred time"
                })
            
            # Move to next 30-minute slot
            current_time += timedelta(minutes=30)
            
            # Skip nights (before 8 AM, after 6 PM)
            if current_time.hour < 8 or current_time.hour >= 18:
                current_time = current_time.replace(hour=8, minute=0) + timedelta(days=1)
        
        return sorted(alternatives, key=lambda x: x['score'], reverse=True)
    
    def can_auto_confirm(self, booking: BookingRequest) -> bool:
        """Check if booking can be automatically confirmed"""
        
        # Check resource rules for auto approval
        auto_approval_rules = ResourceScheduleRule.objects.filter(
            resource=booking.resource,
            rule_type='auto_approval',
            is_active=True
        )
        
        for rule in auto_approval_rules:
            if self._rule_matches_booking(rule, booking):
                return True
        
        # Check if slot is available and no approval required
        if self.is_time_slot_available(booking.resource, booking.requested_start, booking.requested_end):
            require_approval_rules = ResourceScheduleRule.objects.filter(
                resource=booking.resource,
                rule_type='require_approval',
                is_active=True
            )
            
            for rule in require_approval_rules:
                if self._rule_matches_booking(rule, booking):
                    return False
            
            return True
        
        return False
    
    def confirm_booking(self, booking: BookingRequest, confirmed_by=None) -> bool:
        """Confirm a pending booking"""
        
        if booking.status != 'pending':
            return False
        
        if not self.is_time_slot_available(booking.resource, booking.requested_start, booking.requested_end):
            return False
        
        booking.status = 'confirmed'
        booking.save()
        
        # Trigger any service-specific callbacks
        self._notify_source_service(booking, 'confirmed')
        
        return True
    
    def start_booking(self, booking: BookingRequest, started_by) -> bool:
        """Mark booking as in progress"""
        
        if booking.status != 'confirmed':
            return False
        
        booking.status = 'in_progress'
        booking.actual_start = timezone.now()
        booking.save()
        
        self._notify_source_service(booking, 'started')
        return True
    
    def complete_booking(self, booking: BookingRequest, completed_by) -> bool:
        """Mark booking as completed"""

        from services.cflows.signals import booking_status_changed
        
        if booking.status not in ['confirmed', 'in_progress']:
            return False
        
        booking.status = 'completed'
        booking.completed_at = timezone.now()
        booking.completed_by = completed_by
        booking.actual_end = timezone.now()
        
        if not booking.actual_start:
            booking.actual_start = booking.requested_start
        

        booking.save()

        booking_status_changed.sent(sender=BookingRequest, booking=booking, event='completed')
        
        # Notify source service
        self._notify_source_service(booking, 'completed')
        
        return True
    
    def cancel_booking(self, booking: BookingRequest, reason: str = "") -> bool:
        """Cancel a booking"""
        
        if booking.status in ['completed', 'cancelled']:
            return False
        
        booking.status = 'cancelled'
        if reason:
            booking.custom_data['cancellation_reason'] = reason
        booking.save()
        
        self._notify_source_service(booking, 'cancelled')
        return True
    
    def reschedule_booking(
        self,
        booking: BookingRequest,
        new_start: datetime,
        new_end: datetime,
        rescheduled_by=None
    ) -> bool:
        """Reschedule an existing booking"""
        
        if booking.status in ['completed', 'cancelled']:
            return False
        
        # Check if new time slot is available
        if not self.is_time_slot_available(
            booking.resource, new_start, new_end, exclude_booking_id=booking.id
        ):
            return False
        
        # Store old times in custom data for audit
        old_data = {
            'old_start': booking.requested_start.isoformat(),
            'old_end': booking.requested_end.isoformat(),
            'rescheduled_at': timezone.now().isoformat(),
            'rescheduled_by': rescheduled_by.user.get_full_name() if rescheduled_by else None
        }
        booking.custom_data.update(old_data)
        
        booking.requested_start = new_start
        booking.requested_end = new_end
        booking.status = 'rescheduled'
        booking.save()
        
        self._notify_source_service(booking, 'rescheduled')
        return True
    
    def get_resource_utilization_stats(
        self,
        resource: SchedulableResource,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Get utilization statistics for a resource"""
        
        bookings = BookingRequest.objects.filter(
            resource=resource,
            status__in=['confirmed', 'in_progress', 'completed'],
            requested_start__date__gte=start_date,
            requested_end__date__lte=end_date
        )
        
        total_booked_hours = 0
        total_bookings = bookings.count()
        completed_bookings = bookings.filter(status='completed').count()
        
        for booking in bookings:
            duration = booking.requested_end - booking.requested_start
            total_booked_hours += duration.total_seconds() / 3600
        
        # Calculate theoretical max hours (8 hours per day)
        days_count = (end_date - start_date).days + 1
        theoretical_max_hours = days_count * 8 * resource.max_concurrent_bookings
        
        return {
            'total_bookings': total_bookings,
            'completed_bookings': completed_bookings,
            'completion_rate': round((completed_bookings / total_bookings) * 100, 1) if total_bookings > 0 else 0,
            'total_booked_hours': round(total_booked_hours, 2),
            'average_booking_duration': round(total_booked_hours / total_bookings, 2) if total_bookings > 0 else 0,
            'theoretical_max_hours': theoretical_max_hours,
            'utilization_rate': round((total_booked_hours / theoretical_max_hours) * 100, 1) if theoretical_max_hours > 0 else 0,
        }
    
    def _is_date_available(self, resource: SchedulableResource, check_date: date) -> bool:
        """Check if a specific date is available based on availability rules"""
        
        # Check for availability rules
        availability_rules = ResourceScheduleRule.objects.filter(
            resource=resource,
            rule_type='availability',
            is_active=True
        )
        
        if not availability_rules.exists():
            return True  # No rules means always available
        
        for rule in availability_rules:
            if self._date_matches_rule(rule, check_date):
                return True
        
        return False
    
    def _is_datetime_available(self, resource: SchedulableResource, start_time: datetime, end_time: datetime) -> bool:
        """Check if datetime range matches availability rules"""
        
        # Get default availability from resource settings
        default_rules = resource.availability_rules
        if default_rules:
            start_hour = default_rules.get('start_hour', 8)
            end_hour = default_rules.get('end_hour', 18)
            working_days = default_rules.get('working_days', [0, 1, 2, 3, 4])  # Mon-Fri
            
            # Check if booking is within working hours
            if start_time.hour < start_hour or end_time.hour > end_hour:
                return False
            
            # Check if booking is on working days
            if start_time.weekday() not in working_days:
                return False
        
        return True
    
    def _is_blackout_period(self, resource: SchedulableResource, start_time: datetime, end_time: datetime) -> bool:
        """Check if time range conflicts with blackout periods"""
        
        blackout_rules = ResourceScheduleRule.objects.filter(
            resource=resource,
            rule_type='blackout',
            is_active=True
        )
        
        for rule in blackout_rules:
            if self._datetime_matches_rule(rule, start_time, end_time):
                return True
        
        return False
    
    def _get_daily_capacity(self, resource: SchedulableResource, check_date: date) -> float:
        """Get the daily capacity for a resource on a specific date"""
        
        # Check for capacity override rules
        capacity_rules = ResourceScheduleRule.objects.filter(
            resource=resource,
            rule_type='capacity_override',
            is_active=True
        )
        
        for rule in capacity_rules:
            if self._date_matches_rule(rule, check_date):
                return rule.rule_config.get('capacity_hours', 8.0)
        
        # Default to 8 hours
        return 8.0
    
    def _rule_matches_booking(self, rule: ResourceScheduleRule, booking: BookingRequest) -> bool:
        """Check if a rule matches a booking"""
        
        return self._datetime_matches_rule(rule, booking.requested_start, booking.requested_end)
    
    def _date_matches_rule(self, rule: ResourceScheduleRule, check_date: date) -> bool:
        """Check if a date matches a schedule rule"""
        
        # Check date range
        if rule.start_date and check_date < rule.start_date:
            return False
        if rule.end_date and check_date > rule.end_date:
            return False
        
        # Check days of week
        if rule.days_of_week:
            if check_date.weekday() not in rule.days_of_week:
                return False
        
        return True
    
    def _datetime_matches_rule(self, rule: ResourceScheduleRule, start_time: datetime, end_time: datetime) -> bool:
        """Check if a datetime range matches a schedule rule"""
        
        # Check if dates match
        if not self._date_matches_rule(rule, start_time.date()):
            return False
        
        # Check time range
        if rule.start_time and rule.end_time:
            booking_start_time = start_time.time()
            booking_end_time = end_time.time()
            
            # Check if booking overlaps with rule time range
            if (booking_start_time < rule.end_time and booking_end_time > rule.start_time):
                return True
        
        return rule.start_time is None and rule.end_time is None
    
    def _notify_source_service(self, booking: BookingRequest, event: str):
        """Notify the source service about booking changes"""
        
        try:
            if booking.source_service == 'cflows':
                # Import the signal from CFlows
                from services.cflows.signals import booking_status_changed
                
                # Send signal to CFlows
                booking_status_changed.send(
                    sender=self.__class__,
                    booking=booking,
                    event=event
                )
        except Exception as e:
            # Log error but don't fail the operation
            print(f"Failed to notify source service {booking.source_service}: {e}")


class ResourceManagementService:
    """Service for managing schedulable resources"""
    
    def __init__(self, organization):
        self.organization = organization
    
    def create_resource(
        self,
        organization,
        name: str,
        resource_type: str,
        **kwargs
    ) -> SchedulableResource:
        """Creates new resource"""
        
        description = kwargs.get('description', '')
        capacity = kwargs.get('capacity', 1)
        location = kwargs.get('location', '')
        metadata = kwargs.get('metadata', {})
        availability_rules = kwargs.get('availability_rules', {
            'start_hour': 8,
            'end_hour': 18,
            'working_days': [0, 1, 2, 3, 4]  # Mon-Fri
        })
        
        resource = SchedulableResource.objects.create(
            organization=organization,
            name=name,
            resource_type=resource_type,
            description=description,
            max_concurrent_bookings=capacity,
            availability_rules=availability_rules,
            service_type='scheduling',
            is_active=True
        )
        
        return resource
    
    def update_resource(self, resource_id: int, **kwargs) -> Optional[SchedulableResource]:
        """Updates resource properties"""
        try:
            resource = SchedulableResource.objects.get(
                id=resource_id,
                organization=self.organization
            )
            
            # Update allowed fields
            allowed_fields = [
                'name', 'description', 'max_concurrent_bookings',
                'availability_rules', 'is_active'
            ]
            
            for field, value in kwargs.items():
                if field in allowed_fields and hasattr(resource, field):
                    setattr(resource, field, value)
            
            resource.save()
            return resource
            
        except SchedulableResource.DoesNotExist:
            return None
    
    def deactivate_resource(self, resource_id: int) -> bool:
        """Safely deactivates resource"""
        try:
            resource = SchedulableResource.objects.get(
                id=resource_id,
                organization=self.organization
            )
            
            # Check for future bookings
            future_bookings = BookingRequest.objects.filter(
                resource=resource,
                status__in=['pending', 'confirmed'],
                requested_start__gt=timezone.now()
            )
            
            if future_bookings.exists():
                # Don't deactivate if there are future bookings
                return False
            
            resource.is_active = False
            resource.save()
            return True
            
        except SchedulableResource.DoesNotExist:
            return False
    
    def get_available_resources(
        self,
        organization,
        check_datetime: datetime,
        duration: Optional[timedelta] = None
    ) -> List[SchedulableResource]:
        """Gets available resources at time"""
        
        duration = duration or timedelta(hours=1)
        end_datetime = check_datetime + duration
        
        # Get all active resources
        resources = SchedulableResource.objects.filter(
            organization=organization,
            is_active=True
        )
        
        available_resources = []
        scheduling_service = SchedulingService(organization)
        
        for resource in resources:
            if scheduling_service.is_time_slot_available(resource, check_datetime, end_datetime):
                available_resources.append(resource)
        
        return available_resources
    
    def calculate_capacity_utilization(
        self,
        resource: SchedulableResource,
        period: Dict[str, date]
    ) -> Dict[str, Any]:
        """Analyzes capacity usage"""
        
        start_date = period.get('start_date')
        end_date = period.get('end_date')
        
        if not start_date or not end_date:
            raise ValueError("Period must include start_date and end_date")
        
        scheduling_service = SchedulingService(resource.organization)
        return scheduling_service.get_resource_utilization_stats(resource, start_date, end_date)
    
    def create_resource_from_team(self, team) -> SchedulableResource:
        """Create a schedulable resource from a team"""
        
        resource, created = SchedulableResource.objects.get_or_create(
            organization=self.organization,
            linked_team=team,
            defaults={
                'name': team.name,
                'resource_type': 'team',
                'description': f"Schedulable resource for team: {team.name}",
                'max_concurrent_bookings': team.default_capacity,
                'service_type': 'scheduling',
                'availability_rules': {
                    'start_hour': 8,
                    'end_hour': 18,
                    'working_days': [0, 1, 2, 3, 4]  # Mon-Fri
                }
            }
        )
        
        return resource
    
    def sync_team_resources(self) -> List[SchedulableResource]:
        """Sync all teams to schedulable resources"""
        from core.models import Team
        
        resources = []
        teams = Team.objects.filter(organization=self.organization, is_active=True)
        
        for team in teams:
            resource = self.create_resource_from_team(team)
            resources.append(resource)
        
        return resources
    
    def update_resource_capacity(self, resource: SchedulableResource, new_capacity: int):
        """Update resource capacity"""
        resource.max_concurrent_bookings = new_capacity
        resource.save()
        
        # Update linked team if exists
        if resource.linked_team:
            resource.linked_team.default_capacity = new_capacity
            resource.linked_team.save()
    
    def set_resource_availability(
        self,
        resource: SchedulableResource,
        start_hour: int,
        end_hour: int,
        working_days: List[int]
    ):
        """Set resource availability rules"""
        
        availability_rules = resource.availability_rules or {}
        availability_rules.update({
            'start_hour': start_hour,
            'end_hour': end_hour,
            'working_days': working_days
        })
        
        resource.availability_rules = availability_rules
        resource.save()
