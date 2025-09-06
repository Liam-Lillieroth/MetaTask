from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from core.models import Organization, UserProfile, Team
import uuid


class SchedulableResource(models.Model):
    """Generic resource that can be scheduled (teams, equipment, rooms, etc.)"""
    RESOURCE_TYPES = [
        ('team', 'Team'),
        ('equipment', 'Equipment'),
        ('room', 'Room'),
        ('person', 'Person'),
        ('custom', 'Custom')
    ]
    
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPES)
    description = models.TextField(blank=True)
    
    # Capacity settings
    max_concurrent_bookings = models.PositiveIntegerField(default=1)
    default_booking_duration = models.DurationField(default=timezone.timedelta(hours=2))
    
    # Availability settings (JSON for flexibility)
    availability_rules = models.JSONField(default=dict, help_text="Working hours, blackout dates, etc.")
    
    # Integration
    linked_team = models.OneToOneField(Team, on_delete=models.CASCADE, null=True, blank=True)
    external_resource_id = models.CharField(max_length=100, blank=True, help_text="ID in external system")
    service_type = models.CharField(max_length=50, default='scheduling', help_text="Which service manages this resource")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['organization', 'name']
        indexes = [
            models.Index(fields=['organization', 'resource_type', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_resource_type_display()})"


class BookingRequest(models.Model):
    """Flexible booking request that can come from any service"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rescheduled', 'Rescheduled')
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ]
    
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    
    # Request details
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Scheduling
    requested_start = models.DateTimeField()
    requested_end = models.DateTimeField()
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)
    
    # Resource requirements
    resource = models.ForeignKey(SchedulableResource, on_delete=models.CASCADE)
    required_capacity = models.PositiveIntegerField(default=1)
    
    # Metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    
    # Integration with other services
    source_service = models.CharField(max_length=50, help_text="Service that created this booking")
    source_object_type = models.CharField(max_length=50, help_text="Type of object in source service")
    source_object_id = models.CharField(max_length=100, help_text="ID of object in source service")
    
    # People
    requested_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, related_name='requested_bookings')
    assigned_to = models.ManyToManyField(UserProfile, related_name='assigned_bookings', blank=True)
    completed_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='completed_bookings')
    
    # Custom data for service-specific requirements
    custom_data = models.JSONField(default=dict)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['requested_start']
        indexes = [
            models.Index(fields=['organization', 'status', 'requested_start']),
            models.Index(fields=['resource', 'requested_start']),
            models.Index(fields=['source_service', 'source_object_id']),
        ]

    def __str__(self):
        return f"{self.title} - {self.requested_start.strftime('%Y-%m-%d %H:%M')}"

    def duration(self):
        """Return the duration of the booking"""
        return self.requested_end - self.requested_start

    def is_past(self):
        """Check if the booking is in the past"""
        return self.requested_end < timezone.now()

    def is_upcoming(self):
        """Check if the booking is upcoming (within next 24 hours)"""
        now = timezone.now()
        return self.requested_start > now and self.requested_start <= now + timezone.timedelta(hours=24)


class ResourceScheduleRule(models.Model):
    """Flexible rules for resource scheduling"""
    RULE_TYPES = [
        ('availability', 'Availability Window'),
        ('blackout', 'Blackout Period'),
        ('capacity_override', 'Capacity Override'),
        ('auto_approval', 'Auto Approval'),
        ('require_approval', 'Require Approval')
    ]
    
    resource = models.ForeignKey(SchedulableResource, on_delete=models.CASCADE, related_name='schedule_rules')
    rule_type = models.CharField(max_length=20, choices=RULE_TYPES)
    
    # Time-based rules
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    days_of_week = models.JSONField(default=list, help_text="List of weekday numbers (0=Monday)")
    
    # Rule configuration
    rule_config = models.JSONField(default=dict, help_text="Rule-specific configuration")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['resource', 'rule_type']

    def __str__(self):
        return f"{self.resource.name} - {self.get_rule_type_display()}"
