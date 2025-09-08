"""
URL patterns for user management views
"""
from django.urls import path
from . import user_management_views

app_name = 'user_management'

urlpatterns = [
    path('', user_management_views.user_management, name='user_management'),
    path('create/', user_management_views.create_user, name='create_user'),
    path('assign-role/<int:user_id>/', user_management_views.assign_role, name='assign_role'),
    path('api/locations/', user_management_views.get_user_locations, name='api_locations'),
    path('roles/', user_management_views.role_management, name='role_management'),
]
