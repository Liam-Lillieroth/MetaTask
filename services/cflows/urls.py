from django.urls import path
from . import views
from . import transition_views
from . import attachment_views
from . import template_views
from . import calendar_views
from . import notification_views

app_name = 'cflows'

urlpatterns = [
    # Dashboard
    path('', views.index, name='index'),
    
    # Workflows
    path('workflows/', views.workflows_list, name='workflow_list'),
    path('workflows/create/', views.create_workflow, name='create_workflow'),
    path('workflows/<int:workflow_id>/', views.workflow_detail, name='workflow_detail'),
    path('workflows/<int:workflow_id>/save-as-template/', template_views.save_as_template, name='save_as_template'),
    
    # Workflow Templates
    path('templates/', template_views.template_list, name='template_list'),
    path('templates/<int:template_id>/', template_views.template_detail, name='template_detail'),
    path('templates/<int:template_id>/create/', template_views.create_from_template, name='create_from_template'),
    path('templates/<int:template_id>/preview/', template_views.template_preview, name='template_preview'),
    
    # Work Items
    path('work-items/', views.work_items_list, name='work_items_list'),
    path('work-items/<int:work_item_id>/', views.work_item_detail, name='work_item_detail'),
    path('workflows/<int:workflow_id>/work-items/create/', views.create_work_item, name='create_work_item'),
    
    # Work Item Transitions
    path('work-items/<int:work_item_id>/transition/<int:transition_id>/', transition_views.transition_work_item, name='transition_work_item'),
    path('work-items/<int:work_item_id>/transition/<int:transition_id>/form/', transition_views.transition_form, name='transition_form'),
    path('work-items/<int:work_item_id>/assign/', transition_views.assign_work_item, name='assign_work_item'),
    path('work-items/<int:work_item_id>/priority/', transition_views.update_work_item_priority, name='update_work_item_priority'),
    path('work-items/<int:work_item_id>/transitions/', transition_views.get_available_transitions, name='get_available_transitions'),
    
    # Work Item Comments and Attachments
    path('work-items/<int:work_item_id>/comments/add/', attachment_views.add_comment, name='add_comment'),
    path('work-items/<int:work_item_id>/comments/<int:comment_id>/edit/', attachment_views.edit_comment, name='edit_comment'),
    path('work-items/<int:work_item_id>/comments/<int:comment_id>/delete/', attachment_views.delete_comment, name='delete_comment'),
    path('work-items/<int:work_item_id>/attachments/upload/', attachment_views.upload_attachment, name='upload_attachment'),
    path('work-items/<int:work_item_id>/attachments/<int:attachment_id>/download/', attachment_views.download_attachment, name='download_attachment'),
    path('work-items/<int:work_item_id>/attachments/<int:attachment_id>/delete/', attachment_views.delete_attachment, name='delete_attachment'),
    
    # Team Bookings
    path('bookings/', views.team_bookings_list, name='team_bookings_list'),
    
    # Calendar
    path('calendar/', calendar_views.calendar_view, name='calendar'),
    path('calendar/events/', calendar_views.calendar_events, name='calendar_events'),
    path('calendar/bookings/create/', calendar_views.create_booking, name='create_booking'),
    path('calendar/bookings/create/work-item/<int:work_item_id>/step/<int:step_id>/', calendar_views.create_booking_for_work_item, name='create_booking_for_work_item'),
    path('calendar/bookings/<int:booking_id>/', calendar_views.booking_detail, name='booking_detail'),
    path('calendar/bookings/<int:booking_id>/update/', calendar_views.update_booking, name='update_booking'),
    path('calendar/bookings/<int:booking_id>/delete/', calendar_views.delete_booking, name='delete_booking'),
    
    # API endpoints
    path('api/notifications/', notification_views.real_time_notifications, name='api_notifications'),
    path('api/notifications/read/', notification_views.mark_notification_read, name='api_notification_read'),
    path('api/bookings/<int:booking_id>/complete/', views.complete_booking, name='api_complete_booking'),
]