from django import template
from django.urls import reverse, NoReverseMatch
from core.services.permission_service import PermissionService

register = template.Library()

@register.filter
def has_permission(user_profile, permission_codename):
    """
    Template filter to check if user has permission
    Usage: {% if profile|has_permission:'workflow.create' %}
    """
    if not user_profile or not user_profile.organization:
        return False
    
    permission_service = PermissionService(user_profile.organization)
    return permission_service.has_permission(user_profile, permission_codename)

@register.simple_tag
def permission_message(permission_codename):
    """
    Get the user-friendly message for a missing permission
    Usage: {% permission_message 'workflow.create' %}
    """
    # Create a dummy service to get the message
    from core.models import Organization
    try:
        org = Organization.objects.first()  # This is just for getting the message
        if org:
            permission_service = PermissionService(org)
            return permission_service.get_missing_permission_message(permission_codename)
    except:
        pass
    
    return f"You need the '{permission_codename}' permission. Contact your administrator for access."

@register.inclusion_tag('components/permission_button.html')
def permission_button(user_profile, permission_codename, button_text, button_url, button_class="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg", button_icon=None):
    """
    Render a button that's enabled/disabled based on permissions
    Usage: {% permission_button profile 'workflow.create' 'Create Workflow' 'cflows:create_workflow' %}
    """
    if not user_profile or not user_profile.organization:
        has_perm = False
        message = "User profile not found"
    else:
        permission_service = PermissionService(user_profile.organization)
        has_perm = permission_service.has_permission(user_profile, permission_codename)
        message = permission_service.get_missing_permission_message(permission_codename)
    
    # Try to reverse the URL
    try:
        if '/' in button_url:
            # It's already a URL
            resolved_url = button_url
        else:
            # It's a URL name that needs to be reversed
            resolved_url = reverse(button_url)
    except (NoReverseMatch, AttributeError):
        resolved_url = button_url
    
    return {
        'has_permission': has_perm,
        'button_text': button_text,
        'button_url': resolved_url,
        'button_class': button_class,
        'button_icon': button_icon,
        'permission_message': message,
        'permission_codename': permission_codename
    }

@register.simple_tag
def user_permissions(user_profile):
    """
    Get all permissions for a user
    Usage: {% user_permissions profile as perms %}
    """
    if not user_profile or not user_profile.organization:
        return []
    
    permission_service = PermissionService(user_profile.organization)
    user_roles = permission_service.get_user_roles(user_profile)
    
    permissions = set()
    for role in user_roles:
        for permission in role.permissions.all():
            permissions.add(permission.codename)
    
    return list(permissions)

@register.filter
def user_has_any_permission(user_profile, permission_list):
    """
    Check if user has any of the permissions in the list
    Usage: {% if profile|user_has_any_permission:'workflow.create,workflow.edit' %}
    """
    if not user_profile or not user_profile.organization:
        return False
    
    permission_service = PermissionService(user_profile.organization)
    permissions = permission_list.split(',')
    
    for permission in permissions:
        if permission_service.has_permission(user_profile, permission.strip()):
            return True
    
    return False
