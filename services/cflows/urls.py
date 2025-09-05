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
    path('workflows/create-enhanced/', views.create_workflow_enhanced, name='create_workflow_enhanced'),
    path('workflows/<int:workflow_id>/', views.workflow_detail, name='workflow_detail'),
    path('workflows/<int:workflow_id>/save-as-template/', template_views.save_as_template, name='save_as_template'),
    path('workflows/<int:workflow_id>/field-config/', views.workflow_field_config, name='workflow_field_config'),
    
    # Workflow Transitions Management
    path('workflows/<int:workflow_id>/transitions/', views.workflow_transitions_manager, name='workflow_transitions_manager'),
    path('workflows/<int:workflow_id>/transitions/bulk-create/', views.bulk_create_transitions, name='bulk_create_transitions'),
    path('workflows/<int:workflow_id>/steps/<int:from_step_id>/transitions/create/', views.create_workflow_transition, name='create_workflow_transition'),
    path('transitions/<int:transition_id>/edit/', views.edit_workflow_transition, name='edit_workflow_transition'),
    path('transitions/<int:transition_id>/delete/', views.delete_workflow_transition, name='delete_workflow_transition'),
    
    # Quick Access Transition Management (from navbar)
    path('transitions/select-workflow/', views.select_workflow_for_transitions, name='select_workflow_for_transitions'),
    path('transitions/bulk-create/select-workflow/', views.select_workflow_for_bulk_transitions, name='select_workflow_for_bulk_transitions'),
    
    # Workflow Templates
    path('templates/', template_views.template_list, name='template_list'),
    path('templates/<int:template_id>/', template_views.template_detail, name='template_detail'),
    path('templates/<int:template_id>/create/', template_views.create_from_template, name='create_from_template'),
    path('templates/<int:template_id>/preview/', template_views.template_preview, name='template_preview'),
    
    # Work Items
    path('work-items/', views.work_items_list, name='work_items_list'),
    path('work-items/<int:work_item_id>/', views.work_item_detail, name='work_item_detail'),
    path('work-items/create/', views.create_work_item_select_workflow, name='create_work_item_select_workflow'),
    path('workflows/<int:workflow_id>/work-items/create/', views.create_work_item, name='create_work_item'),
    
    # Work Item Transitions
    path('work-items/<int:work_item_id>/transition/<int:transition_id>/', transition_views.transition_work_item, name='transition_work_item'),
    path('work-items/<int:work_item_id>/transition/<int:transition_id>/form/', transition_views.transition_form, name='transition_form'),
    path('work-items/<int:work_item_id>/move-back/<int:step_id>/', transition_views.move_work_item_back, name='move_work_item_back'),
    path('work-items/<int:work_item_id>/move-back/<int:step_id>/form/', transition_views.backward_transition_form, name='backward_transition_form'),
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
    
    # Team Management
    path('teams/', views.teams_list, name='teams_list'),
    path('teams/create/', views.create_team, name='create_team'),
    path('teams/<int:team_id>/', views.team_detail, name='team_detail'),
    path('teams/<int:team_id>/edit/', views.edit_team, name='edit_team'),
    
    # Custom Fields Management
    path('custom-fields/', views.custom_fields_list, name='custom_fields_list'),
    path('custom-fields/create/', views.create_custom_field, name='create_custom_field'),
    path('custom-fields/<int:field_id>/edit/', views.edit_custom_field, name='edit_custom_field'),
    path('custom-fields/<int:field_id>/delete/', views.delete_custom_field, name='delete_custom_field'),
    path('custom-fields/<int:field_id>/toggle/', views.toggle_custom_field, name='toggle_custom_field'),
    
    # Calendar
    path('calendar/', calendar_views.calendar_view, name='calendar'),
    path('calendar/events/', calendar_views.calendar_events, name='calendar_events'),
    path('calendar/bookings/create/', calendar_views.create_booking, name='create_booking'),
    path('calendar/bookings/create/work-item/<int:work_item_id>/step/<int:step_id>/', calendar_views.create_booking_for_work_item, name='create_booking_for_work_item'),
    path('calendar/bookings/<int:booking_id>/', calendar_views.booking_detail, name='booking_detail'),
    path('calendar/bookings/<int:booking_id>/update/', calendar_views.update_booking, name='update_booking'),
    path('calendar/bookings/<int:booking_id>/delete/', calendar_views.delete_booking, name='delete_booking'),
    
    # Calendar Views Management
    path('calendar/views/save/', calendar_views.save_calendar_view, name='save_calendar_view'),
    path('calendar/views/load/<int:view_id>/', calendar_views.load_calendar_view, name='load_calendar_view'),
    path('calendar/views/delete/<int:view_id>/', calendar_views.delete_calendar_view, name='delete_calendar_view'),
    path('calendar/views/list/', calendar_views.get_saved_views, name='get_saved_views'),
    
    # API endpoints
    path('api/notifications/', notification_views.real_time_notifications, name='api_notifications'),
    path('api/notifications/read/', notification_views.mark_notification_read, name='api_notification_read'),
    path('api/bookings/<int:booking_id>/complete/', views.complete_booking, name='api_complete_booking'),
]