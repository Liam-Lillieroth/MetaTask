from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.exceptions import PermissionDenied
from .models import Organization, UserProfile


@login_required
def check_organization_access(request):
    """
    Check if user has access to an organization or needs to create/join one
    """
    try:
        profile = request.user.mediap_profile
        organization = profile.organization
        
        # Check if user is in a personal organization and trying to create another
        if organization.organization_type == 'personal' and request.GET.get('action') == 'create_org':
            return JsonResponse({
                'status': 'error',
                'message': 'Personal account users cannot create additional organizations. Upgrade to a business account for multi-organization access.',
                'can_create': False,
                'current_org': organization.name,
                'org_type': organization.organization_type
            })
        
        return JsonResponse({
            'status': 'success',
            'has_org': True,
            'org_name': organization.name,
            'org_type': organization.organization_type,
            'can_create': organization.organization_type == 'business' or profile.can_create_organizations,
            'is_admin': profile.is_organization_admin
        })
        
    except UserProfile.DoesNotExist:
        # User has no profile, needs to create personal org or join existing
        return JsonResponse({
            'status': 'needs_setup',
            'has_org': False,
            'message': 'You need to create a personal workspace or join an existing organization.',
            'can_create': True
        })


@login_required 
@require_http_methods(["POST"])
def create_personal_organization(request):
    """
    Create a personal organization for a user
    """
    try:
        # Check if user already has a profile/organization
        if hasattr(request.user, 'mediap_profile'):
            return JsonResponse({
                'status': 'error',
                'message': 'You already belong to an organization.'
            })
        
        # Create personal organization
        org_name = f"{request.user.get_full_name() or request.user.username}'s Workspace"
        
        organization = Organization.objects.create(
            name=org_name,
            description=f"Personal workspace for {request.user.get_full_name() or request.user.username}",
            organization_type='personal',
            is_active=True
        )
        
        # Create user profile
        profile = UserProfile.objects.create(
            user=request.user,
            organization=organization,
            is_organization_admin=True,
            has_staff_panel_access=True,
            can_create_organizations=False  # Personal users can't create more orgs
        )
        
        # Set up personal free licenses (this could be done via signals)
        from licensing.models import Service, LicenseType, License
        from django.utils import timezone
        
        for service in Service.objects.filter(allows_personal_free=True):
            try:
                personal_license_type = service.license_types.filter(name='personal_free').first()
                if personal_license_type:
                    License.objects.create(
                        organization=organization,
                        license_type=personal_license_type,
                        account_type='personal',
                        is_personal_free=True,
                        status='active',
                        billing_cycle='lifetime',
                        start_date=timezone.now(),
                        current_users=1,
                        created_by=request.user
                    )
            except Exception as e:
                # Log error but don't fail the org creation
                print(f"Error creating license for {service.name}: {e}")
        
        return JsonResponse({
            'status': 'success',
            'message': f'Created personal workspace: {organization.name}',
            'org_id': organization.id,
            'org_name': organization.name
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Error creating organization: {str(e)}'
        })


@login_required
def organization_required_view(request):
    """
    View that ensures user has an organization before proceeding
    """
    try:
        profile = request.user.mediap_profile
        organization = profile.organization
        
        # Check if organization is active
        if not organization.is_active:
            messages.error(request, 'Your organization is currently inactive. Please contact support.')
            return redirect('accounts:profile')
            
        return None  # Continue to the actual view
        
    except UserProfile.DoesNotExist:
        # Redirect to organization setup
        messages.info(request, 'Please set up your workspace before continuing.')
        return redirect('core:setup_organization')


def require_organization_access(view_func):
    """
    Decorator to require organization access for views
    """
    def wrapped_view(request, *args, **kwargs):
        redirect_response = organization_required_view(request)
        if redirect_response:
            return redirect_response
        return view_func(request, *args, **kwargs)
    return wrapped_view


def require_business_organization(view_func):
    """
    Decorator to require business organization access (not personal)
    """
    def wrapped_view(request, *args, **kwargs):
        redirect_response = organization_required_view(request)
        if redirect_response:
            return redirect_response
            
        try:
            profile = request.user.mediap_profile
            if profile.organization.organization_type == 'personal':
                messages.error(request, 'This feature requires a business organization. Upgrade your account to access team features.')
                return redirect('accounts:profile')
        except UserProfile.DoesNotExist:
            return redirect('core:setup_organization')
            
        return view_func(request, *args, **kwargs)
    return wrapped_view


@login_required
def setup_organization(request):
    """
    Setup page for users who need to create or join an organization
    """
    # Check if user already has an organization
    try:
        profile = request.user.mediap_profile
        messages.info(request, f'You already belong to {profile.organization.name}')
        return redirect('dashboard:dashboard')
    except UserProfile.DoesNotExist:
        pass
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create_personal':
            # Create personal organization
            org_name = f"{request.user.get_full_name() or request.user.username}'s Workspace"
            
            organization = Organization.objects.create(
                name=org_name,
                description=f"Personal workspace for {request.user.get_full_name() or request.user.username}",
                organization_type='personal',
                is_active=True
            )
            
            # Create user profile
            UserProfile.objects.create(
                user=request.user,
                organization=organization,
                is_organization_admin=True,
                has_staff_panel_access=True,
                can_create_organizations=False
            )
            
            messages.success(request, f'Created your personal workspace: {organization.name}')
            return redirect('dashboard:dashboard')
    
    return render(request, 'core/setup_organization.html')
