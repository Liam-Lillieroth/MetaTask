"""
URL patterns for Staff Panel
"""
from django.urls import path
from . import staff_panel_views

# No app_name to avoid namespace conflicts

urlpatterns = [
    # Main dashboard
    path('', staff_panel_views.staff_panel_dashboard, name='staff_dashboard'),
    
    # Organization management
    path('organization/', staff_panel_views.organization_settings, name='staff_organization_settings'),
    
    # User management and analytics
    path('analytics/', staff_panel_views.user_analytics, name='staff_user_analytics'),
    
    # Team management
    path('teams/', staff_panel_views.team_management, name='staff_team_management'),
    
    # Role and permissions
    path('roles/', staff_panel_views.role_permissions, name='staff_role_permissions'),
    
    # Subscription and billing
    path('subscription/', staff_panel_views.subscription_plans, name='staff_subscription_plans'),
    
    # System logs
    path('logs/', staff_panel_views.system_logs, name='staff_system_logs'),
    
    # Integrations
    path('integrations/', staff_panel_views.integrations, name='staff_integrations'),
]
