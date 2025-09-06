"""
URL patterns for role management
"""

from django.urls import path
from . import role_views

urlpatterns = [
    # Role Management Dashboard
    path('', role_views.role_management_dashboard, name='role_dashboard'),
    path('list/', role_views.role_list, name='role_list'),
    path('create/', role_views.role_create, name='role_create'),
    path('<int:role_id>/', role_views.role_detail, name='role_detail'),
    path('<int:role_id>/permissions/', role_views.role_permissions_view, name='role_permissions'),
    
    # User Role Management
    path('user-roles/', role_views.user_roles_view, name='user_roles'),
    path('assign-role/', role_views.assign_role_to_user, name='assign_role'),
    path('remove-role/', role_views.remove_role_from_user, name='remove_role'),
]
