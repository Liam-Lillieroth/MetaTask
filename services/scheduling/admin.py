from django.contrib import admin
from .models import SchedulableResource, BookingRequest, ResourceScheduleRule


@admin.register(SchedulableResource)
class SchedulableResourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'resource_type', 'organization', 'max_concurrent_bookings', 'service_type', 'is_active', 'created_at']
    list_filter = ['resource_type', 'service_type', 'is_active', 'organization', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['is_active', 'max_concurrent_bookings']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'resource_type', 'description', 'is_active')
        }),
        ('Organization & Integration', {
            'fields': ('organization', 'linked_team', 'service_type', 'external_resource_id')
        }),
        ('Capacity & Settings', {
            'fields': ('max_concurrent_bookings', 'default_booking_duration', 'availability_rules')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('organization', 'linked_team')


@admin.register(BookingRequest)
class BookingRequestAdmin(admin.ModelAdmin):
    list_display = ['title', 'resource', 'organization', 'status', 'priority', 'requested_start', 'source_service', 'created_at']
    list_filter = ['status', 'priority', 'resource__resource_type', 'source_service', 'organization', 'created_at']
    search_fields = ['title', 'description', 'source_object_id']
    list_editable = ['status', 'priority']
    readonly_fields = ['uuid', 'created_at', 'updated_at']
    date_hierarchy = 'requested_start'
    
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'status', 'priority')
        }),
        ('Scheduling', {
            'fields': ('resource', 'requested_start', 'requested_end', 'actual_start', 'actual_end', 'required_capacity')
        }),
        ('Organization & People', {
            'fields': ('organization', 'requested_by', 'completed_by')
        }),
        ('Source Integration', {
            'fields': ('source_service', 'source_object_type', 'source_object_id', 'custom_data'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('uuid', 'created_at', 'updated_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'organization', 'resource', 'requested_by', 'completed_by'
        )
    
    actions = ['mark_confirmed', 'mark_completed', 'mark_cancelled']
    
    def mark_confirmed(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='confirmed')
        self.message_user(request, f'{updated} bookings marked as confirmed.')
    mark_confirmed.short_description = 'Mark selected bookings as confirmed'
    
    def mark_completed(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status__in=['confirmed', 'in_progress']).update(
            status='completed', 
            completed_at=timezone.now()
        )
        self.message_user(request, f'{updated} bookings marked as completed.')
    mark_completed.short_description = 'Mark selected bookings as completed'
    
    def mark_cancelled(self, request, queryset):
        updated = queryset.exclude(status__in=['completed', 'cancelled']).update(status='cancelled')
        self.message_user(request, f'{updated} bookings cancelled.')
    mark_cancelled.short_description = 'Cancel selected bookings'


@admin.register(ResourceScheduleRule)
class ResourceScheduleRuleAdmin(admin.ModelAdmin):
    list_display = ['resource', 'rule_type', 'start_date', 'end_date', 'is_active', 'created_at']
    list_filter = ['rule_type', 'is_active', 'created_at']
    search_fields = ['resource__name']
    list_editable = ['is_active']
    readonly_fields = ['created_at']
    
    fieldsets = (
        (None, {
            'fields': ('resource', 'rule_type', 'is_active')
        }),
        ('Time Rules', {
            'fields': ('start_date', 'end_date', 'start_time', 'end_time', 'days_of_week')
        }),
        ('Configuration', {
            'fields': ('rule_config',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('resource')
