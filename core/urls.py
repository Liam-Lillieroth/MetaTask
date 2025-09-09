from django.urls import path, include
from . import views

app_name = 'core'

urlpatterns = [
    path('check-organization/', views.check_organization_access, name='check_organization_access'),
    path('create-personal-org/', views.create_personal_organization, name='create_personal_organization'),
    path('setup/', views.setup_organization, name='setup_organization'),
    
    # Role Management
    path('roles/', include('core.role_urls')),
    
    # User Management
    path('users/', include('core.user_management_urls', namespace='user_management')),
]
