from django.utils import timezone
from django.db.models import Q, Count, Sum
from datetime import date, datetime, timedelta
from typing import Dict, List, Any, Optional
from .models import SchedulableResource, BookingRequest, ResourceScheduleRule


class SchedulingService:
    """Core scheduling business logic"""
    
    def __init__(self, organization):
        self.organization = organization

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
            status__in=['confirmed', 'in_progress', 'pending'],
            requested_start__lt=end_datetime,
            requested_end__gt=start_datetime
        ).select_related('requested_by').order_by('requested_start')
        
        schedule_items = []
        for booking in bookings:
            schedule_items.append({
                'id': booking.id,
                'uuid': str(booking.uuid),
                'title': booking.title,
                'description': booking.description,
                'start': booking.requested_start,
                'end': booking.requested_end,
                'status': booking.status,
                'priority': booking.priority,
                'requested_by': booking.requested_by.get_display_name() if booking.requested_by else None,
                'source_service': booking.source_service,
                'custom_data': booking.custom_data
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
        """Suggest alternative booking times"""
        
        alternatives = []
        search_window = timedelta(days=14)  # Search within 2 weeks
        
        # Search both before and after preferred time
        for offset_hours in range(0, int(search_window.total_seconds() // 3600), 2):
            if len(alternatives) >= max_alternatives:
                break
                
            # Try times after preferred
            candidate_start = preferred_start + timedelta(hours=offset_hours)
            candidate_end = candidate_start + duration
            
            if self.is_time_slot_available(resource, candidate_start, candidate_end):
                alternatives.append({
                    'start_time': candidate_start,
                    'end_time': candidate_end,
                    'offset_hours': offset_hours,
                    'is_preferred': offset_hours == 0
                })
            
            # Try times before preferred (if not the same time)
            if offset_hours > 0:
                candidate_start = preferred_start - timedelta(hours=offset_hours)
                candidate_end = candidate_start + duration
                
                if self.is_time_slot_available(resource, candidate_start, candidate_end):
                    alternatives.append({
                        'start_time': candidate_start,
                        'end_time': candidate_end,
                        'offset_hours': -offset_hours,
                        'is_preferred': False
                    })
        
        return sorted(alternatives, key=lambda x: abs(x['offset_hours']))[:max_alternatives]

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
        
        if booking.status not in ['confirmed', 'in_progress']:
            return False
        
        booking.status = 'completed'
        booking.actual_end = timezone.now()
        booking.completed_by = completed_by
        booking.save()
        
        self._notify_source_service(booking, 'completed')
        return True

    def cancel_booking(self, booking: BookingRequest, cancelled_by) -> bool:
        """Cancel a booking"""
        
        if booking.status in ['completed', 'cancelled']:
            return False
        
        booking.status = 'cancelled'
        booking.save()
        
        self._notify_source_service(booking, 'cancelled')
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
            requested_start__date__lte=end_date
        )
        
        total_bookings = bookings.count()
        total_hours = sum(
            (booking.requested_end - booking.requested_start).total_seconds() / 3600
            for booking in bookings
        )
        
        # Calculate theoretical maximum capacity
        days_in_period = (end_date - start_date).days + 1
        daily_capacity = self._get_daily_capacity(resource, start_date)
        max_possible_hours = days_in_period * daily_capacity
        
        return {
            'total_bookings': total_bookings,
            'total_hours': round(total_hours, 2),
            'max_possible_hours': round(max_possible_hours, 2),
            'utilization_percent': round((total_hours / max_possible_hours) * 100, 1) if max_possible_hours > 0 else 0,
            'average_booking_duration': round(total_hours / total_bookings, 2) if total_bookings > 0 else 0
        }

    def _is_date_available(self, resource: SchedulableResource, check_date: date) -> bool:
        """Check if a specific date is available based on availability rules"""
        
        availability_rules = resource.availability_rules or {}
        working_days = availability_rules.get('working_days', [0, 1, 2, 3, 4])  # Mon-Fri default
        
        # Check if day of week is available (0=Monday, 6=Sunday)
        if check_date.weekday() not in working_days:
            return False
        
        # Check for specific blackout dates
        blackout_dates = availability_rules.get('blackout_dates', [])
        if check_date.isoformat() in blackout_dates:
            return False
        
        return True

    def _is_datetime_available(self, resource: SchedulableResource, start_time: datetime, end_time: datetime) -> bool:
        """Check if datetime range matches availability rules"""
        
        availability_rules = resource.availability_rules or {}
        start_hour = availability_rules.get('start_hour', 9)
        end_hour = availability_rules.get('end_hour', 17)
        
        # Check if booking times are within working hours
        if start_time.hour < start_hour or end_time.hour > end_hour:
            return False
        
        return True

    def _is_blackout_period(self, resource: SchedulableResource, start_time: datetime, end_time: datetime) -> bool:
        """Check if time range conflicts with blackout periods"""
        
        blackout_rules = ResourceScheduleRule.objects.filter(
            resource=resource,
            rule_type='blackout',
            is_active=True,
            effective_start__lte=end_time,
            effective_end__gte=start_time
        )
        
        return blackout_rules.exists()

    def _get_daily_capacity(self, resource: SchedulableResource, check_date: date) -> float:
        """Get the daily capacity for a resource on a specific date"""
        
        availability_rules = resource.availability_rules or {}
        start_hour = availability_rules.get('start_hour', 9)
        end_hour = availability_rules.get('end_hour', 17)
        
        return float(end_hour - start_hour)

    def _rule_matches_booking(self, rule: ResourceScheduleRule, booking: BookingRequest) -> bool:
        """Check if a rule matches a booking"""
        
        # Check if rule is currently effective
        now = timezone.now()
        if rule.effective_start and rule.effective_start > now:
            return False
        if rule.effective_end and rule.effective_end < now:
            return False
        
        # Check rule-specific conditions
        rule_config = rule.rule_config or {}
        
        if rule.rule_type == 'auto_approval':
            # Check conditions like priority, duration, advance booking time
            min_priority = rule_config.get('min_priority')
            if min_priority and booking.priority != min_priority:
                return False
                
            max_duration_hours = rule_config.get('max_duration_hours')
            if max_duration_hours:
                duration_hours = booking.duration().total_seconds() / 3600
                if duration_hours > max_duration_hours:
                    return False
        
        return True

    def _date_matches_rule(self, rule: ResourceScheduleRule, check_date: date) -> bool:
        """Check if a date matches a schedule rule"""
        
        rule_config = rule.rule_config or {}
        
        # Check day of week restrictions
        allowed_days = rule_config.get('allowed_days')
        if allowed_days and check_date.weekday() not in allowed_days:
            return False
        
        return True

    def _datetime_matches_rule(self, rule: ResourceScheduleRule, start_time: datetime, end_time: datetime) -> bool:
        """Check if a datetime range matches a schedule rule"""
        
        rule_config = rule.rule_config or {}
        
        # Check time of day restrictions
        allowed_start_hour = rule_config.get('allowed_start_hour')
        allowed_end_hour = rule_config.get('allowed_end_hour')
        
        if allowed_start_hour and start_time.hour < allowed_start_hour:
            return False
        if allowed_end_hour and end_time.hour > allowed_end_hour:
            return False
        
        return True

    def _notify_source_service(self, booking: BookingRequest, event: str):
        """Notify the source service about booking changes"""
        
        # This is a placeholder for service-specific notifications
        # In a real implementation, this would trigger callbacks to the source service
        # For now, we'll just log the event
        pass


class ResourceManagementService:
    """Service for managing schedulable resources"""
    
    def __init__(self, organization):
        self.organization = organization

    def create_resource(
        self,
        name: str,
        resource_type: str,
        description: str = '',
        max_concurrent_bookings: int = 1,
        linked_team=None,
        service_type: str = 'scheduling'
    ) -> SchedulableResource:
        """Create a new schedulable resource"""
        
        resource = SchedulableResource.objects.create(
            organization=self.organization,
            name=name,
            resource_type=resource_type,
            description=description,
            max_concurrent_bookings=max_concurrent_bookings,
            linked_team=linked_team,
            service_type=service_type
        )
        
        return resource

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

    def add_blackout_period(
        self,
        resource: SchedulableResource,
        start_time: datetime,
        end_time: datetime,
        name: str,
        description: str = ''
    ) -> ResourceScheduleRule:
        """Add a blackout period for a resource"""
        
        rule = ResourceScheduleRule.objects.create(
            resource=resource,
            rule_type='blackout',
            name=name,
            description=description,
            effective_start=start_time,
            effective_end=end_time,
            rule_config={'type': 'blackout_period'}
        )
        
        return rule