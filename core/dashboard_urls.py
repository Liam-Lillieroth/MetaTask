from django.urls import path
from . import dashboard_views

urlpatterns = [
    path('', dashboard_views.dashboard, name='dashboard'),
    path('service/<slug:service_slug>/', dashboard_views.service_access_check, name='service_access_check'),
]
