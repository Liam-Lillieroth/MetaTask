from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from core.models import Organization, UserProfile, Team, JobType, CalendarEvent
import json
import uuid


class WorkflowTemplate(models.Model):
    """Reusable workflow templates"""
    name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=100, default='General')
    
    # Template configuration
    is_public = models.BooleanField(default=False, help_text="Available to all organizations")
    created_by_org = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True, related_name='workflow_templates')
    
    # Template data (JSON structure for steps and transitions)
    template_data = models.JSONField(default=dict, help_text="Template configuration for steps and transitions")
    
    # Metadata
    usage_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.category})"


class Workflow(models.Model):
    """Organization-scoped workflow definitions"""
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='workflows')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Template relationship
    template = models.ForeignKey(WorkflowTemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name='workflows')
    
    # Workflow metadata
    is_active = models.BooleanField(default=True)
    version = models.PositiveIntegerField(default=1)
    
    # Permissions and sharing
    is_shared = models.BooleanField(default=False, help_text="Share with other organizations")
    allowed_organizations = models.ManyToManyField(Organization, blank=True, related_name='shared_workflows')
    
    # Advanced settings
    auto_assign = models.BooleanField(default=False, help_text="Auto-assign work items to team members")
    requires_approval = models.BooleanField(default=False, help_text="Workflow changes require approval")
    
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
    
    # Enhanced content
    title = models.CharField(max_length=200, help_text="Human-readable identifier for this item")
    description = models.TextField(blank=True)
    rich_content = models.TextField(blank=True, help_text="Rich HTML content for detailed descriptions")
    
    # Priority and classification
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    tags = models.JSONField(default=list, help_text="List of tags for categorization")
    
    # Assignment and ownership
    created_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, related_name='created_work_items')
    current_assignee = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_work_items')
    watchers = models.ManyToManyField(UserProfile, blank=True, related_name='watched_work_items')
    
    # Dependencies
    depends_on = models.ManyToManyField('self', symmetrical=False, blank=True, related_name='dependents')
    
    # Due dates and scheduling
    due_date = models.DateTimeField(null=True, blank=True)
    estimated_duration = models.DurationField(null=True, blank=True, help_text="Estimated time to complete")
    
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


class WorkItemAttachment(models.Model):
    """File attachments for work items"""
    work_item = models.ForeignKey(WorkItem, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='cflows/attachments/%Y/%m/%d/')
    filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    content_type = models.CharField(max_length=100)
    
    # Metadata
    uploaded_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.work_item.title} - {self.filename}"


class WorkItemComment(models.Model):
    """Comments and activity on work items"""
    work_item = models.ForeignKey(WorkItem, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True)
    
    # Comment content
    content = models.TextField()
    is_system_comment = models.BooleanField(default=False, help_text="Auto-generated system comment")
    
    # Threading
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_edited = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comment on {self.work_item.title} by {self.author}"


class WorkItemRevision(models.Model):
    """Track revisions of work items for version control"""
    work_item = models.ForeignKey(WorkItem, on_delete=models.CASCADE, related_name='revisions')
    revision_number = models.PositiveIntegerField()
    
    # Snapshot data
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    rich_content = models.TextField(blank=True)
    data = models.JSONField(default=dict)
    
    # Change tracking
    changed_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True)
    change_summary = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['work_item', 'revision_number']
        ordering = ['-revision_number']
    
    def __str__(self):
        return f"{self.work_item.title} v{self.revision_number}"


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


class CustomField(models.Model):
    """Custom fields that organizations can define for their work items"""
    
    FIELD_TYPES = [
        ('text', 'Text Input'),
        ('textarea', 'Text Area'), 
        ('number', 'Number'),
        ('decimal', 'Decimal'),
        ('date', 'Date'),
        ('datetime', 'Date & Time'),
        ('checkbox', 'Checkbox'),
        ('select', 'Dropdown Select'),
        ('multiselect', 'Multiple Select'),
        ('email', 'Email'),
        ('url', 'URL'),
        ('phone', 'Phone Number'),
    ]
    
    # Basic field definition
    organization = models.ForeignKey('core.Organization', on_delete=models.CASCADE, related_name='custom_fields')
    name = models.CharField(max_length=100, help_text="Internal field name (no spaces)")
    label = models.CharField(max_length=200, help_text="Display label for users")
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES, default='text')
    
    # Field configuration
    is_required = models.BooleanField(default=False)
    default_value = models.TextField(blank=True, help_text="Default value (JSON for complex types)")
    help_text = models.CharField(max_length=500, blank=True, help_text="Help text shown to users")
    placeholder = models.CharField(max_length=200, blank=True, help_text="Placeholder text for input fields")
    
    # Validation
    min_length = models.PositiveIntegerField(null=True, blank=True, help_text="Minimum length for text fields")
    max_length = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum length for text fields")
    min_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Minimum value for number fields")
    max_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Maximum value for number fields")
    
    # Select field options (JSON array)
    options = models.JSONField(default=list, blank=True, help_text="Options for select fields (JSON array)")
    
    # Field ordering and organization
    order = models.PositiveIntegerField(default=0, help_text="Display order")
    section = models.CharField(max_length=100, blank=True, help_text="Section to group fields")
    
    # Workflow context - optional workflow filtering
    workflows = models.ManyToManyField(Workflow, blank=True, help_text="Limit to specific workflows (empty = all workflows)")
    workflow_steps = models.ManyToManyField(WorkflowStep, blank=True, help_text="Show only for specific steps")
    
    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['section', 'order', 'label']
        unique_together = ['organization', 'name']
    
    def __str__(self):
        return f"{self.organization.name} - {self.label}"
    
    def get_form_field(self):
        """Generate Django form field based on field type"""
        from django import forms
        
        field_class = forms.CharField
        widget_attrs = {
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500'
        }
        
        if self.placeholder:
            widget_attrs['placeholder'] = self.placeholder
        
        field_kwargs = {
            'label': self.label,
            'required': self.is_required,
            'help_text': self.help_text,
        }
        
        if self.field_type == 'text':
            if self.max_length:
                field_kwargs['max_length'] = self.max_length
            if self.min_length:
                field_kwargs['min_length'] = self.min_length
            field_class = forms.CharField
            widget_attrs.update({'type': 'text'})
            
        elif self.field_type == 'textarea':
            field_class = forms.CharField
            widget_attrs.update({'rows': '4'})
            field_kwargs['widget'] = forms.Textarea(attrs=widget_attrs)
            
        elif self.field_type == 'number':
            field_class = forms.IntegerField
            widget_attrs.update({'type': 'number'})
            if self.min_value is not None:
                field_kwargs['min_value'] = int(self.min_value)
            if self.max_value is not None:
                field_kwargs['max_value'] = int(self.max_value)
                
        elif self.field_type == 'decimal':
            field_class = forms.DecimalField
            widget_attrs.update({'type': 'number', 'step': '0.01'})
            if self.min_value is not None:
                field_kwargs['min_value'] = self.min_value
            if self.max_value is not None:
                field_kwargs['max_value'] = self.max_value
                
        elif self.field_type == 'date':
            field_class = forms.DateField
            widget_attrs.update({'type': 'date'})
            
        elif self.field_type == 'datetime':
            field_class = forms.DateTimeField
            widget_attrs.update({'type': 'datetime-local'})
            
        elif self.field_type == 'checkbox':
            field_class = forms.BooleanField
            widget_attrs = {'class': 'rounded text-purple-600 focus:ring-purple-500'}
            field_kwargs['widget'] = forms.CheckboxInput(attrs=widget_attrs)
            
        elif self.field_type == 'select':
            field_class = forms.ChoiceField
            choices = [(opt, opt) for opt in self.options] if self.options else []
            field_kwargs['choices'] = [('', '-- Select --')] + choices
            field_kwargs['widget'] = forms.Select(attrs=widget_attrs)
            
        elif self.field_type == 'multiselect':
            field_class = forms.MultipleChoiceField
            choices = [(opt, opt) for opt in self.options] if self.options else []
            field_kwargs['choices'] = choices
            widget_attrs.update({'multiple': True, 'size': min(len(choices), 5)})
            field_kwargs['widget'] = forms.SelectMultiple(attrs=widget_attrs)
            
        elif self.field_type == 'email':
            field_class = forms.EmailField
            widget_attrs.update({'type': 'email'})
            
        elif self.field_type == 'url':
            field_class = forms.URLField
            widget_attrs.update({'type': 'url'})
            
        elif self.field_type == 'phone':
            field_class = forms.CharField
            widget_attrs.update({'type': 'tel'})
        
        # Set default widget if not already set
        if 'widget' not in field_kwargs:
            if self.field_type == 'checkbox':
                pass  # Already set above
            else:
                field_kwargs['widget'] = forms.TextInput(attrs=widget_attrs) if field_class == forms.CharField else None
        
        # Set default value
        if self.default_value and self.field_type != 'checkbox':
            field_kwargs['initial'] = self.default_value
        elif self.field_type == 'checkbox' and self.default_value:
            field_kwargs['initial'] = self.default_value.lower() in ['true', '1', 'yes']
        
        return field_class(**field_kwargs)


class WorkItemCustomFieldValue(models.Model):
    """Values for custom fields on work items"""
    
    work_item = models.ForeignKey(WorkItem, on_delete=models.CASCADE, related_name='custom_field_values')
    custom_field = models.ForeignKey(CustomField, on_delete=models.CASCADE)
    workflow_step = models.ForeignKey(WorkflowStep, on_delete=models.CASCADE, help_text="Step where this data was collected")
    
    # Store value as text - will be converted based on field type
    value = models.TextField(blank=True)
    
    # Track when this was collected
    collected_by = models.ForeignKey('core.UserProfile', on_delete=models.SET_NULL, null=True, help_text="User who provided this data")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['work_item', 'custom_field']
    
    def __str__(self):
        return f"{self.work_item.title} - {self.custom_field.label}: {self.value[:50]}"
    
    def get_display_value(self):
        """Get formatted value for display"""
        if not self.value:
            return ''
            
        field_type = self.custom_field.field_type
        
        if field_type == 'checkbox':
            return 'Yes' if self.value.lower() in ['true', '1', 'yes'] else 'No'
        elif field_type in ['date', 'datetime']:
            try:
                from django.utils import timezone
                if field_type == 'date':
                    date_obj = timezone.datetime.strptime(self.value, '%Y-%m-%d').date()
                    return date_obj.strftime('%B %d, %Y')
                else:
                    datetime_obj = timezone.datetime.fromisoformat(self.value.replace('Z', '+00:00'))
                    return datetime_obj.strftime('%B %d, %Y at %I:%M %p')
            except (ValueError, AttributeError):
                return self.value
        elif field_type == 'multiselect':
            try:
                import json
                values = json.loads(self.value) if isinstance(self.value, str) else self.value
                return ', '.join(values) if isinstance(values, list) else str(values)
            except (json.JSONDecodeError, TypeError):
                return self.value
        else:
            return self.value
    
    def set_value(self, value):
        """Set value with proper formatting"""
        if self.custom_field.field_type == 'multiselect' and isinstance(value, list):
            import json
            self.value = json.dumps(value)
        elif self.custom_field.field_type == 'checkbox':
            self.value = str(bool(value)).lower()
        else:
            self.value = str(value) if value is not None else ''


class StepDataCollection(models.Model):
    """Tracks when a work item needs custom data collection for a step"""
    
    work_item = models.ForeignKey(WorkItem, on_delete=models.CASCADE, related_name='step_data_collections')
    workflow_step = models.ForeignKey(WorkflowStep, on_delete=models.CASCADE)
    
    # Status of data collection
    is_completed = models.BooleanField(default=False)
    completed_by = models.ForeignKey('core.UserProfile', on_delete=models.SET_NULL, null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Track when this was initiated
    initiated_by = models.ForeignKey('core.UserProfile', on_delete=models.SET_NULL, null=True, related_name='initiated_data_collections')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['work_item', 'workflow_step']
    
    def __str__(self):
        return f"{self.work_item.title} - {self.workflow_step.name} data collection"
    
    def get_required_fields(self):
        """Get required custom fields for this step"""
        return self.workflow_step.custom_fields.filter(is_required=True)
    
    def get_optional_fields(self):
        """Get optional custom fields for this step"""
        return self.workflow_step.custom_fields.filter(is_required=False)
    
    def has_all_required_data(self):
        """Check if all required fields have been filled"""
        required_fields = self.get_required_fields()
        for field in required_fields:
            try:
                value = WorkItemCustomFieldValue.objects.get(
                    work_item=self.work_item,
                    custom_field=field
                )
                if not value.value:  # Empty values count as missing
                    return False
            except WorkItemCustomFieldValue.DoesNotExist:
                return False
        return True
