from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html
from .models import Organization, UserProfile, Team, JobType, CalendarEvent


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'user_count', 'team_count', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            user_count=Count('members', distinct=True),
            team_count=Count('teams', distinct=True)
        )
    
    def user_count(self, obj):
        return obj.user_count
    user_count.short_description = 'Users'
    user_count.admin_order_field = 'user_count'
    
    def team_count(self, obj):
        return obj.team_count
    team_count.short_description = 'Teams'
    team_count.admin_order_field = 'team_count'


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_name', 'organization', 'title', 'department', 'is_active']
    list_filter = ['organization', 'is_organization_admin', 'is_active']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'user__email', 'department']
    raw_id_fields = ['user', 'organization']
    readonly_fields = ['created_at', 'updated_at']
    
    def full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    full_name.short_description = 'Full Name'
    full_name.admin_order_field = 'user__first_name'


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization', 'member_count', 'is_active']
    list_filter = ['organization', 'is_active']
    search_fields = ['name', 'description']
    filter_horizontal = ['members']
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(members_count=Count('members'))
    
    def member_count(self, obj):
        return obj.members_count if hasattr(obj, 'members_count') else obj.member_count
    member_count.short_description = 'Members'
    member_count.admin_order_field = 'members_count'


@admin.register(JobType)
class JobTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization', 'default_duration_hours', 'color_preview', 'is_active']
    list_filter = ['organization', 'is_active']
    search_fields = ['name', 'description']
    
    def color_preview(self, obj):
        return format_html(
            '<span style="background-color: {}; padding: 2px 8px; color: white; border-radius: 3px;">{}</span>',
            obj.color,
            obj.color
        )
    color_preview.short_description = 'Color'


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ['title', 'organization', 'event_type', 'start_time', 'end_time', 'created_by', 'color_preview']
    list_filter = ['organization', 'event_type', 'is_all_day', 'start_time', 'related_team']
    search_fields = ['title', 'description']
    raw_id_fields = ['created_by', 'related_team']
    filter_horizontal = ['invitees']
    readonly_fields = ['uuid', 'created_at', 'updated_at']
    
    def color_preview(self, obj):
        return format_html(
            '<span style="background-color: {}; padding: 2px 8px; color: white; border-radius: 3px;">{}</span>',
            obj.color,
            obj.color
        )
    color_preview.short_description = 'Color'
