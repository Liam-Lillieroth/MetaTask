from django.contrib import admin
from django.utils.html import format_html
from .models import Service, LicenseType, License, LicenseUsageLog


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'version', 'allows_personal_free', 'is_active', 'sort_order']
    list_filter = ['is_active', 'allows_personal_free', 'created_at']
    search_fields = ['name', 'slug', 'description']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['sort_order', 'name']


@admin.register(LicenseType)
class LicenseTypeAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'service', 'name', 'price_monthly', 'price_yearly', 'max_users', 'max_workflows', 'is_active']
    list_filter = ['service', 'name', 'is_active', 'is_personal_only', 'requires_organization']
    search_fields = ['display_name', 'service__name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('service', 'name', 'display_name', 'is_active')
        }),
        ('Pricing', {
            'fields': ('price_monthly', 'price_yearly')
        }),
        ('Limits', {
            'fields': ('max_users', 'max_projects', 'max_workflows', 'max_storage_gb', 'max_api_calls_per_day')
        }),
        ('Features & Restrictions', {
            'fields': ('features', 'restrictions'),
            'classes': ('collapse',)
        }),
        ('Account Types', {
            'fields': ('is_personal_only', 'requires_organization')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    list_display = ['organization', 'license_type', 'account_type', 'status', 'usage_summary', 'start_date', 'end_date']
    list_filter = ['status', 'account_type', 'is_personal_free', 'license_type__service', 'billing_cycle']
    search_fields = ['organization__name', 'license_type__display_name', 'notes']
    raw_id_fields = ['organization', 'created_by']
    readonly_fields = ['created_at', 'updated_at', 'usage_summary']
    date_hierarchy = 'start_date'
    
    fieldsets = (
        (None, {
            'fields': ('organization', 'license_type', 'status')
        }),
        ('Account Information', {
            'fields': ('account_type', 'is_personal_free')
        }),
        ('License Period', {
            'fields': ('start_date', 'end_date', 'trial_end_date', 'billing_cycle')
        }),
        ('Usage Tracking', {
            'fields': ('usage_summary', 'current_users', 'current_projects', 'current_workflows', 'current_storage_gb')
        }),
        ('API Usage', {
            'fields': ('current_api_calls_today', 'api_calls_reset_date'),
            'classes': ('collapse',)
        }),
        ('Billing', {
            'fields': ('last_billing_date', 'next_billing_date', 'amount_paid'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('notes', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def usage_summary(self, obj):
        """Display usage summary as colored bars"""
        html = []
        for resource in ['users', 'projects', 'workflows', 'storage_gb']:
            percentage = obj.usage_percentage(resource)
            if percentage > 0:
                color = '#dc3545' if percentage >= 90 else '#ffc107' if percentage >= 75 else '#28a745'
                html.append(
                    f'<div style="margin: 2px 0;"><strong>{resource.replace("_", " ").title()}:</strong> '
                    f'<div style="display: inline-block; width: 100px; height: 10px; background: #f8f9fa; border-radius: 5px; margin: 0 5px;">'
                    f'<div style="width: {percentage}%; height: 100%; background: {color}; border-radius: 5px;"></div></div> '
                    f'{percentage:.1f}%</div>'
                )
        return format_html(''.join(html)) if html else 'No usage data'
    usage_summary.short_description = 'Usage'


@admin.register(LicenseUsageLog)
class LicenseUsageLogAdmin(admin.ModelAdmin):
    list_display = ['license', 'users_count', 'projects_count', 'storage_gb', 'api_calls', 'recorded_at']
    list_filter = ['recorded_at', 'license__license_type__service']
    search_fields = ['license__organization__name']
    raw_id_fields = ['license']
    readonly_fields = ['recorded_at']
    date_hierarchy = 'recorded_at'
    
    def has_add_permission(self, request):
        return False  # Usage logs are created automatically
