from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Registration flow - starts with account type selection
    path('register/', views.AccountTypeSelectionView.as_view(), name='register'),
    path('register/personal/', views.PersonalRegistrationView.as_view(), name='personal_register'),
    path('register/business/', views.BusinessRegistrationView.as_view(), name='business_register'),
    path('register/organization/', views.OrganizationCreationView.as_view(), name='create_organization'),
    path('register/invite-members/', views.InviteMembersView.as_view(), name='invite_members'),
    
    # Authentication
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
]
