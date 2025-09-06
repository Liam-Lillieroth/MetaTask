from django.urls import path
from . import views

app_name = 'scheduling'

urlpatterns = [
    path('', views.index, name='index'),
    path('calendar/', views.calendar_view, name='calendar'),
    
    # Resource management
    path('resources/', views.resource_list, name='resource_list'),
    path('resources/create/', views.create_resource, name='create_resource'),
    path('resources/<int:resource_id>/', views.resource_detail, name='resource_detail'),
    path('sync-teams/', views.sync_teams, name='sync_teams'),
    
    # Booking management  
    path('bookings/', views.booking_list, name='booking_list'),
    path('bookings/create/', views.create_booking, name='create_booking'),
    path('bookings/<int:booking_id>/', views.booking_detail, name='booking_detail'),
    path('bookings/<int:booking_id>/<str:action>/', views.booking_action, name='booking_action'),
    path('bookings/<uuid:booking_uuid>/complete/', views.complete_booking, name='complete_booking'),
    path('bookings/<uuid:booking_uuid>/complete-workflow/', views.complete_booking_workflow_prompt, name='complete_booking_workflow'),
    
    # API endpoints
    path('api/calendar-events/', views.api_calendar_events, name='api_calendar_events'),
    path('api/suggest-times/', views.api_suggest_times, name='api_suggest_times'),
    path('api/check-availability/', views.api_check_availability, name='api_check_availability'),
    
    # Integration
    path('sync-cflows/', views.sync_cflows_bookings, name='sync_cflows_bookings'),
]
