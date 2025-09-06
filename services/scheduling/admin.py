from django.contrib import admin
from .models import SchedulableResource, BookingRequest, ResourceScheduleRule


@admin.register(SchedulableResource)
class SchedulableResourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'resource_type', 'organization', 'max_concurrent_bookings', 'service_type', 'is_active']
    list_filter = ['resource_type', 'service_type', 'is_active', 'organization']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('organization', 'name', 'resource_type', 'description')
        }),
        ('Capacity Settings', {
            'fields': ('max_concurrent_bookings', 'default_booking_duration', 'availability_rules')
        }),
        ('Integration', {
            'fields': ('linked_team', 'external_resource_id', 'service_type')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(BookingRequest)
class BookingRequestAdmin(admin.ModelAdmin):
    list_display = ['title', 'resource', 'status', 'priority', 'requested_start', 'requested_end', 'requested_by', 'source_service']
    list_filter = ['status', 'priority', 'source_service', 'organization', 'requested_start']
    search_fields = ['title', 'description', 'source_object_id']
    readonly_fields = ['uuid', 'created_at', 'updated_at', 'duration_display']
    date_hierarchy = 'requested_start'
    
    fieldsets = (
        (None, {
            'fields': ('organization', 'title', 'description', 'uuid')
        }),
        ('Scheduling', {
            'fields': ('resource', 'requested_start', 'requested_end', 'actual_start', 'actual_end', 'required_capacity')
        }),
        ('Status & Priority', {
            'fields': ('status', 'priority')
        }),
        ('Integration', {
            'fields': ('source_service', 'source_object_type', 'source_object_id', 'custom_data')
        }),
        ('People', {
            'fields': ('requested_by', 'assigned_to', 'completed_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'duration_display'),
            'classes': ('collapse',)
        })
    )
    
    filter_horizontal = ['assigned_to']
    
    def duration_display(self, obj):
        """Display the duration of the booking"""
        return obj.duration()
    duration_display.short_description = 'Duration'


@admin.register(ResourceScheduleRule)
class ResourceScheduleRuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'resource', 'rule_type', 'priority', 'is_active', 'effective_start', 'effective_end']
    list_filter = ['rule_type', 'is_active', 'resource__organization']
    search_fields = ['name', 'description', 'resource__name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('resource', 'rule_type', 'name', 'description')
        }),
        ('Rule Configuration', {
            'fields': ('rule_config', 'priority')
        }),
        ('Effective Period', {
            'fields': ('effective_start', 'effective_end')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )