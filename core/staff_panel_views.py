"""
Staff Panel views for organizational administration
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.utils import timezone
from core.models import Organization, UserProfile, Team
from core.permissions import Role, Permission, UserRoleAssignment
from core.views import require_organization_access
from datetime import timedelta


def get_user_profile(request):
    """Get user profile for the current user"""
    if not request.user.is_authenticated:
        return None
    
    try:
        return request.user.mediap_profile
    except UserProfile.DoesNotExist:
        return None


def require_staff_access(view_func):
    """Decorator to require staff panel access"""
    def wrapper(request, *args, **kwargs):
        profile = get_user_profile(request)
        if not profile:
            messages.error(request, 'Profile not found.')
            return redirect('core:dashboard')
        
        if not (profile.has_staff_panel_access or profile.is_organization_admin):
            messages.error(request, 'You do not have access to the staff panel.')
            return redirect('core:dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
@require_organization_access
@require_staff_access
def staff_panel_dashboard(request):
    """Staff panel dashboard with organization overview"""
    profile = request.user.mediap_profile
    organization = profile.organization
    
    # Get organization statistics
    total_users = UserProfile.objects.filter(organization=organization).count()
    
    # Calculate user growth
    from datetime import datetime, timedelta
    current_month = datetime.now().replace(day=1)
    users_this_month = UserProfile.objects.filter(
        organization=organization,
        user__date_joined__gte=current_month
    ).count()
    
    # Get location statistics from user profiles
    location_stats = []
    locations = UserProfile.objects.filter(
        organization=organization
    ).exclude(location='').values('location').distinct()
    
    for loc in locations:
        if loc['location']:
            user_count = UserProfile.objects.filter(
                organization=organization,
                location=loc['location']
            ).count()
            location_stats.append({
                'name': loc['location'],
                'country': 'Unknown',  # We don't have country data in the simple CharField
                'country_code': 'xx',
                'user_count': user_count
            })
    
    # Get department statistics
    department_stats = []
    departments = UserProfile.objects.filter(
        organization=organization
    ).values('department').distinct()
    
    for dept in departments:
        if dept['department']:
            count = UserProfile.objects.filter(
                organization=organization,
                department=dept['department']
            ).count()
            department_stats.append({
                'name': dept['department'],
                'count': count
            })
    
    # Get recent activities (placeholder)
    recent_activities = [
        {
            'action': 'user_created',
            'description': 'New user John Doe added to London office',
            'timestamp': datetime.now() - timedelta(hours=2)
        },
        {
            'action': 'role_assigned',
            'description': 'HR Manager role assigned to Jane Smith',
            'timestamp': datetime.now() - timedelta(hours=5)
        }
    ]
    
    context = {
        'organization': organization,
        'profile': profile,
        'total_users': total_users,
        'users_this_month': users_this_month,
        'total_locations': len(location_stats),
        'countries_count': 1,  # Simplified since we don't have country data
        'total_departments': len(department_stats),
        'active_teams': len(department_stats),  # Placeholder
        'total_roles': Role.objects.count(),
        'permissions_count': Permission.objects.count(),
        'recent_activities': recent_activities,
        'location_stats': location_stats,
        'active_tasks': 3,  # Placeholder
    }
    
    return render(request, 'core/staff_panel/dashboard.html', context)


@login_required
@require_organization_access
@require_staff_access
def organization_settings(request):
    """Organization settings and configuration"""
    profile = request.user.mediap_profile
    organization = profile.organization
    
    if request.method == 'POST':
        # Handle form submission
        organization.name = request.POST.get('name', organization.name)
        organization.website = request.POST.get('website', organization.website or '')
        organization.description = request.POST.get('description', organization.description or '')
        organization.contact_email = request.POST.get('contact_email', organization.contact_email or '')
        organization.phone = request.POST.get('phone', organization.phone or '')
        organization.address = request.POST.get('address', organization.address or '')
        
        # Handle logo upload
        if 'logo' in request.FILES:
            organization.logo = request.FILES['logo']
        
        try:
            organization.save()
            messages.success(request, 'Organization settings updated successfully.')
        except Exception as e:
            messages.error(request, f'Error updating settings: {str(e)}')
        
        return redirect('core:staff_organization_settings')
    
    # Create a simple form context
    form_data = {
        'name': organization.name,
        'website': getattr(organization, 'website', ''),
        'description': getattr(organization, 'description', ''),
        'contact_email': getattr(organization, 'contact_email', ''),
        'phone': getattr(organization, 'phone', ''),
        'address': getattr(organization, 'address', ''),
    }
    
    # Create form field objects with proper attributes
    class FormField:
        def __init__(self, value='', field_type='text'):
            self.value = value
            self.field_type = field_type
            self.id_for_label = f'id_{field_type}'
            
        def __str__(self):
            if self.field_type == 'textarea':
                return f'<textarea name="{self.field_type}" id="{self.id_for_label}" class="form-control">{self.value}</textarea>'
            else:
                return f'<input type="text" name="{self.field_type}" id="{self.id_for_label}" value="{self.value}" class="form-control">'
    
    form = type('Form', (), {
        'name': FormField(form_data['name'], 'name'),
        'website': FormField(form_data['website'], 'website'),
        'description': FormField(form_data['description'], 'description'),
        'contact_email': FormField(form_data['contact_email'], 'contact_email'),
        'phone': FormField(form_data['phone'], 'phone'),
        'address': FormField(form_data['address'], 'address'),
        'timezone': FormField('UTC', 'timezone'),
        'date_format': FormField('YYYY-MM-DD', 'date_format'),
        'logo': FormField('', 'logo'),
    })()
    
    context = {
        'organization': organization,
        'profile': profile,
        'form': form,
    }
    
    return render(request, 'core/staff_panel/organization_settings.html', context)


@login_required
@require_organization_access
@require_staff_access
def user_analytics(request):
    """Detailed user analytics and statistics"""
    profile = request.user.mediap_profile
    organization = profile.organization
    
    from datetime import datetime, timedelta
    
    # Basic statistics
    total_users = UserProfile.objects.filter(organization=organization).count()
    
    # Active users (logged in within last 30 days)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    active_users = UserProfile.objects.filter(
        organization=organization,
        user__last_login__gte=thirty_days_ago
    ).count()
    
    # New users this month
    current_month = datetime.now().replace(day=1)
    new_users_this_month = UserProfile.objects.filter(
        organization=organization,
        user__date_joined__gte=current_month
    ).count()
    
    # Calculate growth percentage
    last_month = (current_month - timedelta(days=1)).replace(day=1)
    last_month_users = UserProfile.objects.filter(
        organization=organization,
        user__date_joined__gte=last_month,
        user__date_joined__lt=current_month
    ).count()
    
    growth_percentage = 0
    if last_month_users > 0:
        growth_percentage = round(((new_users_this_month - last_month_users) / last_month_users) * 100, 1)
    
    # Department statistics
    department_stats = []
    departments = UserProfile.objects.filter(
        organization=organization
    ).values('department').distinct()
    
    colors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4']
    
    for i, dept in enumerate(departments):
        if dept['department']:
            count = UserProfile.objects.filter(
                organization=organization,
                department=dept['department']
            ).count()
            percentage = round((count / total_users) * 100, 1) if total_users > 0 else 0
            department_stats.append({
                'name': dept['department'],
                'count': count,
                'percentage': percentage,
                'color': colors[i % len(colors)]
            })
    
    # Location statistics
    location_stats = []
    locations = UserProfile.objects.filter(
        organization=organization
    ).exclude(location='').values('location').distinct()
    
    for loc in locations:
        if loc['location']:
            user_count = UserProfile.objects.filter(
                organization=organization,
                location=loc['location']
            ).count()
            
            active_count = UserProfile.objects.filter(
                organization=organization,
                location=loc['location'],
                user__last_login__gte=thirty_days_ago
            ).count()
            
            new_count = UserProfile.objects.filter(
                organization=organization,
                location=loc['location'],
                user__date_joined__gte=current_month
            ).count()
            
            location_stats.append({
                'city': loc['location'],
                'country': 'Unknown',
                'country_code': 'xx',
                'user_count': user_count,
                'active_users': active_count,
                'new_users': new_count
            })
    
    # Role statistics
    role_stats = []
    for role in Role.objects.all():
        user_count = UserRoleAssignment.objects.filter(
            user_profile__organization=organization,
            role=role
        ).count()
        
        if user_count > 0:
            percentage = round((user_count / total_users) * 100, 1) if total_users > 0 else 0
            role_stats.append({
                'name': role.name,
                'user_count': user_count,
                'percentage': percentage
            })
    
    # Weekdays and hours for heatmap
    weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    hours = list(range(24))
    
    # Sample data for charts (would be replaced with real data)
    user_growth_data = [10, 15, 18, 25, 30, 35, 40]
    department_data = [item['count'] for item in department_stats]
    
    context = {
        'organization': organization,
        'profile': profile,
        'total_users': total_users,
        'active_users': active_users,
        'new_users_this_month': new_users_this_month,
        'growth_percentage': abs(growth_percentage),
        'department_stats': department_stats,
        'location_stats': location_stats,
        'role_stats': role_stats,
        'weekdays': weekdays,
        'hours': hours,
        'user_growth_data': user_growth_data,
        'department_data': department_data,
    }
    
    return render(request, 'core/staff_panel/user_analytics.html', context)


@login_required
@require_organization_access
@require_staff_access
def team_management(request):
    """Team management interface"""
    profile = get_user_profile(request)
    organization = profile.organization
    
    # Get teams with member counts
    teams = organization.teams.annotate(
        member_count=Count('members')
    ).prefetch_related('members', 'manager').order_by('name')
    
    # Team hierarchy (top-level teams)
    top_level_teams = teams.filter(parent_team__isnull=True)
    
    context = {
        'profile': profile,
        'organization': organization,
        'teams': teams,
        'top_level_teams': top_level_teams,
    }
    
    return render(request, 'core/staff_panel/team_management.html', context)


@login_required
@require_organization_access
@require_staff_access
def role_permissions(request):
    """Role and permissions management"""
    profile = get_user_profile(request)
    organization = profile.organization
    
    try:
        # Get roles with permission counts
        roles = organization.roles.annotate(
            permission_count=Count('permissions'),
            user_count=Count('user_assignments')
        ).order_by('name')
        
        # Get all available permissions
        permissions = Permission.objects.all().order_by('category', 'name')
        
        # Group permissions by category
        permission_categories = {}
        for perm in permissions:
            if perm.category not in permission_categories:
                permission_categories[perm.category] = []
            permission_categories[perm.category].append(perm)
        
    except Exception as e:
        roles = []
        permission_categories = {}
        messages.warning(request, 'Role management system not fully configured.')
    
    context = {
        'profile': profile,
        'organization': organization,
        'roles': roles,
        'permission_categories': permission_categories,
    }
    
    return render(request, 'core/staff_panel/role_permissions.html', context)


@login_required
@require_organization_access
@require_staff_access
def subscription_plans(request):
    """Subscription plans and billing management"""
    profile = request.user.mediap_profile
    organization = profile.organization
    
    from datetime import datetime, timedelta
    
    # Current plan information (placeholder data)
    current_plan = {
        'name': 'Professional',
        'description': 'Perfect for growing organizations',
        'monthly_price': '99',
        'max_users': '100'
    }
    
    # Next billing date
    next_billing_date = datetime.now() + timedelta(days=28)
    billing_status = 'Active'
    
    # Sample billing history
    billing_history = [
        {
            'date': datetime.now() - timedelta(days=30),
            'description': 'Professional Plan - Monthly',
            'amount': '99.00',
            'status': 'paid'
        },
        {
            'date': datetime.now() - timedelta(days=60),
            'description': 'Professional Plan - Monthly',
            'amount': '99.00',
            'status': 'paid'
        }
    ]
    
    # Current usage statistics
    current_users = UserProfile.objects.filter(organization=organization).count()
    plan_limit_users = 100
    user_usage_percentage = min((current_users / plan_limit_users) * 100, 100)
    
    current_locations = UserProfile.objects.filter(
        organization=organization
    ).exclude(location='').values('location').distinct().count()
    plan_limit_locations = None  # Unlimited for Professional
    location_usage_percentage = 50  # Placeholder
    
    storage_used = 2.5  # GB
    storage_limit = 10  # GB
    storage_usage_percentage = (storage_used / storage_limit) * 100
    
    # Payment method (placeholder)
    payment_method = {
        'last_four': '4242',
        'expiry': '12/25'
    }
    
    context = {
        'organization': organization,
        'profile': profile,
        'current_plan': current_plan,
        'next_billing_date': next_billing_date,
        'billing_status': billing_status,
        'billing_history': billing_history,
        'current_users': current_users,
        'plan_limit_users': plan_limit_users,
        'user_usage_percentage': user_usage_percentage,
        'current_locations': current_locations,
        'plan_limit_locations': plan_limit_locations,
        'location_usage_percentage': location_usage_percentage,
        'storage_used': storage_used,
        'storage_limit': storage_limit,
        'storage_usage_percentage': storage_usage_percentage,
        'payment_method': payment_method,
    }
    
    return render(request, 'core/staff_panel/subscription_plans.html', context)


@login_required
@require_organization_access
@require_staff_access
def system_logs(request):
    """System logs and audit trail"""
    profile = get_user_profile(request)
    organization = profile.organization
    
    # Mock audit log data (replace with actual logging system)
    audit_logs = [
        {
            'timestamp': timezone.now() - timedelta(hours=1),
            'user': 'admin@company.com',
            'action': 'User Created',
            'details': 'Created user: john.doe@company.com',
            'ip_address': '192.168.1.100'
        },
        {
            'timestamp': timezone.now() - timedelta(hours=2),
            'user': 'hr@company.com',
            'action': 'Role Assigned',
            'details': 'Assigned HR Manager role to sarah.johnson@company.com',
            'ip_address': '192.168.1.101'
        },
        {
            'timestamp': timezone.now() - timedelta(hours=3),
            'user': 'admin@company.com',
            'action': 'Settings Updated',
            'details': 'Updated organization timezone to UTC',
            'ip_address': '192.168.1.100'
        },
    ]
    
    context = {
        'profile': profile,
        'organization': organization,
        'audit_logs': audit_logs,
    }
    
    return render(request, 'core/staff_panel/system_logs.html', context)


@login_required
@require_organization_access
@require_staff_access
def integrations(request):
    """Third-party integrations management"""
    profile = get_user_profile(request)
    organization = profile.organization
    
    # Mock integration data
    available_integrations = [
        {
            'name': 'Slack',
            'description': 'Send notifications and updates to Slack channels',
            'icon': 'fab fa-slack',
            'status': 'connected',
            'config_url': '#'
        },
        {
            'name': 'Microsoft Teams',
            'description': 'Integrate with Microsoft Teams for collaboration',
            'icon': 'fab fa-microsoft',
            'status': 'available',
            'config_url': '#'
        },
        {
            'name': 'Google Workspace',
            'description': 'Connect with Google Calendar and Drive',
            'icon': 'fab fa-google',
            'status': 'available',
            'config_url': '#'
        },
        {
            'name': 'Zapier',
            'description': 'Connect with 3000+ apps through Zapier',
            'icon': 'fas fa-bolt',
            'status': 'available',
            'config_url': '#'
        },
    ]
    
    context = {
        'profile': profile,
        'organization': organization,
        'integrations': available_integrations,
    }
    
    return render(request, 'core/staff_panel/integrations.html', context)
