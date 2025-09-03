from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from core.models import Organization, UserProfile, Team, JobType, CalendarEvent
import json
import uuid


class Workflow(models.Model):
    """Organization-scoped workflow definitions"""
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='workflows')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Workflow metadata
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, related_name='created_workflows')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['organization', 'name']
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.organization.name})"


class WorkflowStep(models.Model):
    """Individual steps within a workflow"""
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='steps')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Step ordering and flow
    order = models.PositiveIntegerField(help_text="Order of this step in the workflow")
    
    # Team assignment
    assigned_team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_steps')
    
    # Capacity booking requirements
    requires_booking = models.BooleanField(default=False, help_text="Does this step require capacity booking?")
    estimated_duration_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Estimated time for this step")
    
    # Terminal state
    is_terminal = models.BooleanField(default=False, help_text="Is this a completion/end step?")
    
    # Custom data schema for this step (JSON)
    data_schema = models.JSONField(default=dict, blank=True, help_text="JSON schema for custom data at this step")
    
    class Meta:
        unique_together = ['workflow', 'name']
        ordering = ['workflow', 'order']
    
    def __str__(self):
        return f"{self.workflow.name} - {self.name}"


class WorkflowTransition(models.Model):
    """Define allowed transitions between workflow steps"""
    from_step = models.ForeignKey(WorkflowStep, on_delete=models.CASCADE, related_name='outgoing_transitions')
    to_step = models.ForeignKey(WorkflowStep, on_delete=models.CASCADE, related_name='incoming_transitions')
    
    label = models.CharField(max_length=100, blank=True, help_text="Optional label for this transition (e.g., 'Approve', 'Reject')")
    
    # Conditional logic (for future expansion)
    condition = models.JSONField(default=dict, blank=True, help_text="Optional conditions for this transition")
    
    class Meta:
        unique_together = ['from_step', 'to_step']
    
    def __str__(self):
        label_text = f" ({self.label})" if self.label else ""
        return f"{self.from_step.name} → {self.to_step.name}{label_text}"


class WorkItem(models.Model):
    """Individual instances of workflows - the items being processed"""
    # Unique identifier
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Workflow context
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='work_items')
    current_step = models.ForeignKey(WorkflowStep, on_delete=models.PROTECT, related_name='current_work_items')
    
    # Custom title/identifier
    title = models.CharField(max_length=200, help_text="Human-readable identifier for this item")
    description = models.TextField(blank=True)
    
    # Assignment and ownership
    created_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, related_name='created_work_items')
    current_assignee = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_work_items')
    
    # Custom data storage (JSON)
    data = models.JSONField(default=dict, help_text="Custom data specific to this work item")
    
    # Status tracking
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.title} ({self.workflow.name})"
    
    def save(self, *args, **kwargs):
        # Mark as completed if in terminal step
        if self.current_step.is_terminal and not self.is_completed:
            self.is_completed = True
            self.completed_at = timezone.now()
        elif not self.current_step.is_terminal and self.is_completed:
            self.is_completed = False
            self.completed_at = None
        
        super().save(*args, **kwargs)


class WorkItemHistory(models.Model):
    """Track the history of work item progression through workflow"""
    work_item = models.ForeignKey(WorkItem, on_delete=models.CASCADE, related_name='history')
    
    # Step transition
    from_step = models.ForeignKey(WorkflowStep, on_delete=models.PROTECT, null=True, blank=True, related_name='history_from')
    to_step = models.ForeignKey(WorkflowStep, on_delete=models.PROTECT, related_name='history_to')
    
    # Who made the change
    changed_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True)
    
    # Optional notes about the transition
    notes = models.TextField(blank=True)
    
    # Data snapshot at time of transition
    data_snapshot = models.JSONField(default=dict)
    
    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        from_text = f"from {self.from_step.name}" if self.from_step else "started"
        return f"{self.work_item.title}: {from_text} to {self.to_step.name}"


class TeamBooking(models.Model):
    """Team capacity bookings for workflow steps - CFlows specific scheduling"""
    # Booking identification
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Context
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='cflows_bookings')
    work_item = models.ForeignKey('WorkItem', on_delete=models.CASCADE, related_name='bookings', null=True, blank=True)
    workflow_step = models.ForeignKey('WorkflowStep', on_delete=models.CASCADE, related_name='bookings', null=True, blank=True)
    
    # Job details
    job_type = models.ForeignKey(JobType, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Scheduling
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    
    # Capacity
    required_members = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    
    # Booking management
    booked_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, related_name='created_cflows_bookings')
    assigned_members = models.ManyToManyField(UserProfile, related_name='assigned_cflows_bookings', blank=True)
    
    # Status
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='completed_cflows_bookings')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['start_time']
    
    def __str__(self):
        return f"{self.team.name}: {self.title} ({self.start_time.strftime('%Y-%m-%d %H:%M')})"
