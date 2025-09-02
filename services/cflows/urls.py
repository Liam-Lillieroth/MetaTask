from django.urls import path
from . import views

app_name = 'cflows'

urlpatterns = [
    path('', views.index, name='index'),
    path('workflows/', views.workflows_list, name='workflows_list'),
    path('workflows/create/', views.create_workflow, name='create_workflow'),
    path('workflows/<uuid:pk>/', views.workflow_detail, name='workflow_detail'),
]