from django.urls import path
from . import views

app_name = 'licensing'

urlpatterns = [
    # Customer Support Views
    path('', views.license_dashboard, name='dashboard'),
    path('organizations/', views.organization_licenses, name='organization_licenses'),
    path('organizations/<int:org_id>/', views.organization_licenses, name='organization_detail'),
    path('create-custom-license/', views.create_custom_license, name='create_custom_license'),
    
    # Organization Management Views
    path('manage/', views.organization_license_management, name='organization_management'),
    
    # AJAX/API Views
    path('check-access/<str:service_slug>/', views.check_user_access, name='check_user_access'),
    
    # Access Control Views
    path('access-denied/<str:service_slug>/', views.service_access_denied, name='access_denied'),
]
