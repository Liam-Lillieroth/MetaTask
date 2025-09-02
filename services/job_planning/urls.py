from django.urls import path
from . import views

app_name = 'job_planning'

urlpatterns = [
    path('', views.index, name='index'),
    path('projects/', views.projects_list, name='projects_list'),
    path('projects/create/', views.create_project, name='create_project'),
    path('projects/<uuid:pk>/', views.project_detail, name='project_detail'),
]