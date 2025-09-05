from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from core.models import Organization, UserProfile, Team, JobType, CalendarEvent
from .models import (
    Workflow, WorkflowStep, WorkflowTransition,
    WorkItem, WorkItemHistory, TeamBooking,
    CustomField, WorkItemCustomFieldValue, CalendarView
)


# Only register CFlows-specific models here
# Core models (Organization, UserProfile, Team, JobType, CalendarEvent) 
# are registered in core/admin.py


class WorkflowStepInline(admin.TabularInline):
    model = WorkflowStep
    extra = 1
    fields = ['name', 'order', 'assigned_team', 'requires_booking', 'is_terminal']
    ordering = ['order']


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization', 'step_count', 'work_item_count', 'is_active', 'created_by', 'created_at']
    list_filter = ['organization', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    raw_id_fields = ['created_by']
    inlines = [WorkflowStepInline]
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            step_count=Count('steps', distinct=True),
            work_item_count=Count('work_items', distinct=True)
        )
    
    def step_count(self, obj):
        return obj.step_count
    step_count.short_description = 'Steps'
    step_count.admin_order_field = 'step_count'
    
    def work_item_count(self, obj):
        return obj.work_item_count
    work_item_count.short_description = 'Work Items'
    work_item_count.admin_order_field = 'work_item_count'


class WorkflowTransitionInline(admin.TabularInline):
    model = WorkflowTransition
    fk_name = 'from_step'
    extra = 1
    fields = ['to_step', 'label']


@admin.register(WorkflowStep)
class WorkflowStepAdmin(admin.ModelAdmin):
    list_display = ['name', 'workflow', 'organization_name', 'order', 'assigned_team', 'requires_booking', 'is_terminal']
    list_filter = ['workflow__organization', 'workflow', 'assigned_team', 'requires_booking', 'is_terminal']
    search_fields = ['name', 'description', 'workflow__name']
    raw_id_fields = ['workflow', 'assigned_team']
    inlines = [WorkflowTransitionInline]
    
    def organization_name(self, obj):
        return obj.workflow.organization.name
    organization_name.short_description = 'Organization'
    organization_name.admin_order_field = 'workflow__organization__name'





class WorkItemHistoryInline(admin.TabularInline):
    model = WorkItemHistory
    extra = 0
    fields = ['from_step', 'to_step', 'changed_by', 'notes', 'created_at']
    readonly_fields = ['created_at']
    ordering = ['-created_at']


@admin.register(WorkItem)
class WorkItemAdmin(admin.ModelAdmin):
    list_display = ['title', 'workflow', 'current_step', 'current_assignee', 'is_completed', 'created_by', 'updated_at']
    list_filter = ['workflow__organization', 'workflow', 'current_step', 'is_completed', 'created_at']
    search_fields = ['title', 'description', 'uuid']
    raw_id_fields = ['workflow', 'current_step', 'created_by', 'current_assignee']
    readonly_fields = ['uuid', 'created_at', 'updated_at', 'completed_at']
    inlines = [WorkItemHistoryInline]
    
    fieldsets = (
        (None, {
            'fields': ('uuid', 'title', 'description')
        }),
        ('Workflow Context', {
            'fields': ('workflow', 'current_step', 'current_assignee')
        }),
        ('Status', {
            'fields': ('is_completed', 'completed_at')
        }),
        ('Data', {
            'fields': ('data',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )





@admin.register(TeamBooking)
class TeamBookingAdmin(admin.ModelAdmin):
    list_display = ['title', 'team', 'work_item', 'start_time', 'end_time', 'required_members', 'is_completed', 'booked_by']
    list_filter = ['team__organization', 'team', 'job_type', 'is_completed', 'start_time']
    search_fields = ['title', 'description', 'work_item__title', 'uuid']
    raw_id_fields = ['team', 'work_item', 'workflow_step', 'job_type', 'booked_by', 'completed_by']
    filter_horizontal = ['assigned_members']
    readonly_fields = ['uuid', 'created_at', 'updated_at', 'completed_at']
    
    fieldsets = (
        (None, {
            'fields': ('uuid', 'title', 'description')
        }),
        ('Context', {
            'fields': ('team', 'work_item', 'workflow_step', 'job_type')
        }),
        ('Scheduling', {
            'fields': ('start_time', 'end_time', 'required_members')
        }),
        ('Assignment', {
            'fields': ('booked_by', 'assigned_members')
        }),
        ('Completion', {
            'fields': ('is_completed', 'completed_at', 'completed_by')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )





@admin.register(WorkItemHistory)
class WorkItemHistoryAdmin(admin.ModelAdmin):
    list_display = ['work_item', 'from_step', 'to_step', 'changed_by', 'created_at']
    list_filter = ['work_item__workflow__organization', 'work_item__workflow', 'from_step', 'to_step', 'created_at']
    search_fields = ['work_item__title', 'notes']
    raw_id_fields = ['work_item', 'from_step', 'to_step', 'changed_by']
    readonly_fields = ['created_at']


@admin.register(WorkflowTransition)
class WorkflowTransitionAdmin(admin.ModelAdmin):
    list_display = ['from_step', 'to_step', 'label', 'workflow_name']
    list_filter = ['from_step__workflow__organization', 'from_step__workflow']
    search_fields = ['from_step__name', 'to_step__name', 'label']
    raw_id_fields = ['from_step', 'to_step']
    
    def workflow_name(self, obj):
        return obj.from_step.workflow.name
    workflow_name.short_description = 'Workflow'
    workflow_name.admin_order_field = 'from_step__workflow__name'


@admin.register(CustomField)
class CustomFieldAdmin(admin.ModelAdmin):
    list_display = ['label', 'name', 'field_type', 'organization', 'is_required', 'section', 'order', 'is_active']
    list_filter = ['organization', 'field_type', 'is_required', 'is_active', 'section']
    search_fields = ['name', 'label', 'help_text']
    ordering = ['organization', 'section', 'order', 'label']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('organization', 'name', 'label', 'field_type', 'is_active')
        }),
        ('Field Configuration', {
            'fields': ('is_required', 'default_value', 'help_text', 'placeholder')
        }),
        ('Validation', {
            'fields': ('min_length', 'max_length', 'min_value', 'max_value', 'options'),
            'classes': ('collapse',)
        }),
        ('Organization', {
            'fields': ('section', 'order')
        }),
        ('Workflow Context', {
            'fields': ('workflows', 'workflow_steps'),
            'classes': ('collapse',),
            'description': 'Leave empty to show field for all workflows/steps'
        }),
    )
    
    filter_horizontal = ['workflows', 'workflow_steps']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('organization')


@admin.register(WorkItemCustomFieldValue)
class WorkItemCustomFieldValueAdmin(admin.ModelAdmin):
    list_display = ['work_item', 'custom_field', 'display_value', 'updated_at']
    list_filter = ['custom_field__organization', 'custom_field', 'work_item__workflow']
    search_fields = ['work_item__title', 'custom_field__label', 'value']
    raw_id_fields = ['work_item', 'custom_field']
    readonly_fields = ['created_at', 'updated_at']
    
    def display_value(self, obj):
        return obj.get_display_value()[:100]
    display_value.short_description = 'Value'


@admin.register(CalendarView)
class CalendarViewAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'is_default', 'created_at']
    list_filter = ['is_default', 'created_at']
    search_fields = ['name', 'user__user__first_name', 'user__user__last_name']
    raw_id_fields = ['user']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'user', 'is_default')
        }),
        ('Filter Settings', {
            'fields': ('teams', 'job_types', 'workflows', 'status', 'event_type', 'booked_by'),
            'description': 'JSON fields containing filter values'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
