"""
Role management views for organization administrators
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db import transaction
from django.core.paginator import Paginator
from django.utils import timezone

from accounts.models import UserProfile
from core.models import Organization
from core.permissions import Role, Permission, UserRoleAssignment
from core.services.permission_service import PermissionService
from core.decorators import (
    require_organization_admin, 
    require_role_management, 
    PermissionMixin
)


@require_organization_admin
def role_management_dashboard(request):
    """Dashboard for role management"""
    organization = request.user.profile.organization
    
    # Get statistics
    total_roles = Role.objects.filter(organization=organization, is_active=True).count()
    total_users_with_roles = UserRoleAssignment.objects.filter(
        role__organization=organization,
        is_active=True
    ).values('user_profile').distinct().count()
    
    # Recent role assignments
    recent_assignments = UserRoleAssignment.objects.filter(
        role__organization=organization,
        is_active=True
    ).select_related(
        'user_profile__user', 'role', 'assigned_by__user'
    ).order_by('-created_at')[:10]
    
    context = {
        'organization': organization,
        'total_roles': total_roles,
        'total_users_with_roles': total_users_with_roles,
        'recent_assignments': recent_assignments,
    }
    
    return render(request, 'core/role_management/dashboard.html', context)


@require_role_management
def role_list(request):
    """List all roles in organization"""
    organization = request.user.profile.organization
    
    roles = Role.objects.filter(
        organization=organization,
        is_active=True
    ).prefetch_related('permissions')
    
    # Add user count to each role
    for role in roles:
        role.user_count = role.get_user_count()
    
    context = {
        'roles': roles,
        'organization': organization,
    }
    
    return render(request, 'core/role_management/role_list.html', context)


@require_role_management
def role_create(request):
    """Create new role"""
    organization = request.user.profile.organization
    permission_service = PermissionService(organization)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        role_type = request.POST.get('role_type', 'custom')
        color = request.POST.get('color', '#6B7280')
        max_users = request.POST.get('max_users')
        permission_ids = request.POST.getlist('permissions')
        
        try:
            with transaction.atomic():
                # Create role
                role = Role.objects.create(
                    organization=organization,
                    name=name,
                    description=description,
                    role_type=role_type,
                    color=color,
                    max_users=int(max_users) if max_users else None,
                    created_by=request.user.profile
                )
                
                # Assign permissions
                if permission_ids:
                    permissions = Permission.objects.filter(id__in=permission_ids)
                    role.permissions.set(permissions)
                
                messages.success(request, f"Role '{name}' created successfully!")
                return redirect('core:role_detail', role_id=role.id)
                
        except Exception as e:
            messages.error(request, f"Error creating role: {str(e)}")
    
    # Get available permissions grouped by category
    grouped_permissions = permission_service.get_available_permissions()
    
    context = {
        'grouped_permissions': grouped_permissions,
        'organization': organization,
    }
    
    return render(request, 'core/role_management/role_create.html', context)


@require_role_management
def role_detail(request, role_id):
    """Role detail view"""
    organization = request.user.profile.organization
    role = get_object_or_404(
        Role, 
        id=role_id, 
        organization=organization,
        is_active=True
    )
    
    # Get users with this role
    assignments = UserRoleAssignment.objects.filter(
        role=role,
        is_active=True
    ).select_related('user_profile__user').order_by('created_at')
    
    # Paginate assignments
    paginator = Paginator(assignments, 20)
    page_number = request.GET.get('page')
    assignments_page = paginator.get_page(page_number)
    
    context = {
        'role': role,
        'assignments': assignments_page,
        'user_count': role.get_user_count(),
        'organization': organization,
    }
    
    return render(request, 'core/role_management/role_detail.html', context)


@require_role_management
def assign_role_to_user(request):
    """Assign role to user via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    organization = request.user.profile.organization
    permission_service = PermissionService(organization)
    
    try:
        user_profile_id = request.POST.get('user_profile_id')
        role_id = request.POST.get('role_id')
        notes = request.POST.get('notes', '')
        
        user_profile = get_object_or_404(UserProfile, id=user_profile_id)
        role = get_object_or_404(
            Role, 
            id=role_id, 
            organization=organization,
            is_active=True
        )
        
        # Check if user is in the same organization
        if user_profile.organization != organization:
            return JsonResponse({
                'error': 'User is not in the same organization'
            }, status=403)
        
        assignment = permission_service.assign_role_to_user(
            user_profile=user_profile,
            role=role,
            assigned_by=request.user.profile,
            notes=notes
        )
        
        return JsonResponse({
            'success': True,
            'message': f"Role '{role.name}' assigned to {user_profile.user.get_full_name() or user_profile.user.username}",
            'assignment_id': assignment.id
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_role_management
def remove_role_from_user(request):
    """Remove role from user via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    organization = request.user.profile.organization
    
    try:
        assignment_id = request.POST.get('assignment_id')
        
        assignment = get_object_or_404(
            UserRoleAssignment,
            id=assignment_id,
            role__organization=organization,
            is_active=True
        )
        
        # Deactivate assignment
        assignment.is_active = False
        assignment.deactivated_by = request.user.profile
        assignment.deactivated_at = timezone.now()
        assignment.save()
        
        return JsonResponse({
            'success': True,
            'message': f"Role '{assignment.role.name}' removed from {assignment.user_profile.user.get_full_name() or assignment.user_profile.user.username}"
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_role_management
def user_roles_view(request):
    """View and manage user role assignments"""
    organization = request.user.profile.organization
    
    # Get all user profiles in organization
    user_profiles = UserProfile.objects.filter(
        user__organization_memberships__organization=organization,
        user__organization_memberships__is_active=True
    ).select_related('user').prefetch_related('user_role_assignments__role')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        user_profiles = user_profiles.filter(
            user__username__icontains=search_query
        ) | user_profiles.filter(
            user__first_name__icontains=search_query
        ) | user_profiles.filter(
            user__last_name__icontains=search_query
        )
    
    # Paginate
    paginator = Paginator(user_profiles, 20)
    page_number = request.GET.get('page')
    users_page = paginator.get_page(page_number)
    
    # Get available roles for assignment
    available_roles = Role.objects.filter(
        organization=organization,
        is_active=True
    ).order_by('name')
    
    context = {
        'users': users_page,
        'available_roles': available_roles,
        'search_query': search_query,
        'organization': organization,
    }
    
    return render(request, 'core/role_management/user_roles.html', context)


@require_role_management 
def role_permissions_view(request, role_id):
    """View and edit role permissions"""
    organization = request.user.profile.organization
    role = get_object_or_404(
        Role,
        id=role_id,
        organization=organization,
        is_active=True
    )
    
    permission_service = PermissionService(organization)
    
    if request.method == 'POST':
        permission_ids = request.POST.getlist('permissions')
        
        try:
            with transaction.atomic():
                permissions = Permission.objects.filter(id__in=permission_ids)
                role.permissions.set(permissions)
                
                messages.success(request, f"Permissions updated for role '{role.name}'")
                return redirect('core:role_detail', role_id=role.id)
                
        except Exception as e:
            messages.error(request, f"Error updating permissions: {str(e)}")
    
    # Get permissions grouped by category
    grouped_permissions = permission_service.get_available_permissions()
    current_permission_ids = set(role.permissions.values_list('id', flat=True))
    
    context = {
        'role': role,
        'grouped_permissions': grouped_permissions,
        'current_permission_ids': current_permission_ids,
        'organization': organization,
    }
    
    return render(request, 'core/role_management/role_permissions.html', context)
