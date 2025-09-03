from django.urls import path
from . import views

app_name = 'cflows'

urlpatterns = [
    # Dashboard
    path('', views.index, name='index'),
    
    # Workflows
    path('workflows/', views.workflows_list, name='workflows_list'),
    path('workflows/create/', views.create_workflow, name='create_workflow'),
    path('workflows/<uuid:pk>/', views.workflow_detail, name='workflow_detail'),
    
    # Work Items
    path('work-items/', views.work_items_list, name='work_items_list'),
    path('work-items/<uuid:uuid>/', views.work_item_detail, name='work_item_detail'),
    
    # Team Bookings
    path('bookings/', views.team_bookings_list, name='team_bookings_list'),
    
    # Calendar
    path('calendar/', views.calendar_view, name='calendar'),
]