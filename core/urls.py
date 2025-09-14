"""
URL configuration for MetaTask project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('dashboard/', include(('core.dashboard_urls', 'dashboard'), namespace='dashboard')),
    path('', include('homepage.urls')),
    path('accounts/', include('accounts.urls')),
    path('core/', include('core.urls')),
    path('services/cflows/', include('services.cflows.urls')),
    path('services/scheduling/', include('services.scheduling.urls')),
    path('services/staff-panel/', include('services.staff_panel.urls')),
    path('licensing/', include('licensing.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
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
