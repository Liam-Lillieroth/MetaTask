from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Organization, OrganizationMember, UserRole, UserProfile


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Admin interface for CustomUser model
    """
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': (
                'phone_number', 'referral_source', 'team_size', 
                'job_title', 'organization_name'
            )
        }),
        ('GDPR Compliance', {
            'fields': (
                'privacy_policy_accepted', 'privacy_policy_accepted_date',
                'terms_accepted', 'terms_accepted_date', 'marketing_consent'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'created_at')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'referral_source', 'team_size')
    search_fields = ('username', 'first_name', 'last_name', 'email')


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    """
    Admin interface for Organization model
    """
    list_display = ('name', 'owner', 'company_type', 'team_size', 'is_active', 'created_at')
    list_filter = ('company_type', 'purpose', 'is_active', 'team_size')
    search_fields = ('name', 'owner__username', 'owner__email', 'contact_email')
    readonly_fields = ('slug', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'owner', 'description', 'website')
        }),
        ('Business Details', {
            'fields': ('company_type', 'purpose', 'team_size')
        }),
        ('Contact Information', {
            'fields': ('contact_email', 'contact_phone')
        }),
        ('Address', {
            'fields': ('address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country')
        }),
        ('Settings', {
            'fields': ('is_active', 'max_users')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(OrganizationMember)
class OrganizationMemberAdmin(admin.ModelAdmin):
    """
    Admin interface for OrganizationMember model
    """
    list_display = ('user', 'organization', 'role', 'is_active', 'created_at')
    list_filter = ('role', 'is_active')
    search_fields = ('user__username', 'user__email', 'organization__name')
    readonly_fields = ('created_at',)


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    """
    Admin interface for UserRole model
    """
    list_display = ('user', 'role', 'service', 'is_active', 'granted_at')
    list_filter = ('role', 'service', 'is_active')
    search_fields = ('user__username', 'user__email', 'service')
    readonly_fields = ('granted_at',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Admin interface for UserProfile model
    """
    list_display = ('user', 'email_notifications', 'push_notifications', 'digest_frequency', 'analytics_consent')
    list_filter = ('email_notifications', 'push_notifications', 'digest_frequency', 'analytics_consent')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('last_activity', 'login_count', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Profile Info', {
            'fields': ('user', 'avatar', 'bio', 'website')
        }),
        ('Notification Preferences', {
            'fields': ('email_notifications', 'push_notifications', 'digest_frequency')
        }),
        ('Analytics & Activity', {
            'fields': ('analytics_consent', 'last_activity', 'login_count')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
