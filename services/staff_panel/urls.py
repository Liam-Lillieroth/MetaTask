from django.urls import path
from . import views

app_name = 'staff_panel'

urlpatterns = [
    path('', views.staff_panel_dashboard, name='dashboard'),
    path('organization/', views.organization_settings, name='organization_settings'),
    path('analytics/', views.user_analytics, name='user_analytics'),
    path('teams/', views.team_management, name='team_management'),
    path('roles/', views.role_permissions, name='role_permissions'),
    path('roles/<int:role_id>/permissions/', views.get_role_permissions, name='get_role_permissions'),
    path('licenses/', views.license_management, name='license_management'),
    path('licenses/assign/', views.assign_user_license, name='assign_user_license'),
    path('licenses/revoke/', views.revoke_user_license, name='revoke_user_license'),
    path('licenses/create-custom/', views.create_custom_license, name='create_custom_license'),
    path('subscription/', views.subscription_plans, name='subscription_plans'),
    path('logs/', views.system_logs, name='system_logs'),
    path('integrations/', views.integrations, name='integrations'),
    path('integrations/<str:integration_name>/configure/', views.configure_integration, name='configure_integration'),
    path('integrations/<str:integration_name>/test/', views.test_integration, name='test_integration'),
]
