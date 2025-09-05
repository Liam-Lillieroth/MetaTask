from django import template
from services.cflows.models import WorkflowTransition

register = template.Library()

@register.filter
def can_user_execute(transition, user_profile, work_item=None):
    """Check if a user can execute a transition"""
    if hasattr(transition, 'can_user_execute'):
        return transition.can_user_execute(user_profile, work_item)
    return True

@register.simple_tag
def can_user_execute_tag(transition, user_profile, work_item=None):
    """Template tag version of can_user_execute"""
    if hasattr(transition, 'can_user_execute'):
        return transition.can_user_execute(user_profile, work_item)
    return True
