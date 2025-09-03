from django.shortcuts import render
from django.http import HttpResponse


def index(request):
    """CFlows homepage"""
    return HttpResponse("CFlows - Workflow Management System (To be implemented)")


def workflows_list(request):
    """List workflows"""
    return HttpResponse("Workflows list - To be implemented")


def create_workflow(request):
    """Create new workflow"""
    return HttpResponse("Create workflow - To be implemented")


from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Prefetch
from django.utils import timezone
from core.models import Organization, UserProfile, Team, JobType, CalendarEvent
from core.views import require_organization_access, require_business_organization
from .models import (
    Workflow, WorkflowStep, WorkflowTransition,
    WorkItem, WorkItemHistory, TeamBooking
)


def get_user_profile(request):
    """Get or create user profile for the current user"""
    if not request.user.is_authenticated:
        return None
    
    try:
        return request.user.mediap_profile
    except UserProfile.DoesNotExist:
        # For now, return None if no profile exists
        # In a real app, you might redirect to a profile setup page
        return None


@login_required
@require_organization_access
def index(request):
    """CFlows homepage - Dashboard"""
    profile = request.user.mediap_profile
    
    if not profile:
        return render(request, 'cflows/no_profile.html')
    
    organization = profile.organization
    
    # Get dashboard statistics
    stats = {
        'total_workflows': organization.workflows.filter(is_active=True).count(),
        'active_work_items': WorkItem.objects.filter(
            workflow__organization=organization,
            is_completed=False
        ).count(),
        'my_assigned_items': WorkItem.objects.filter(
            workflow__organization=organization,
            current_assignee=profile,
            is_completed=False
        ).count(),
        'my_teams_count': profile.teams.filter(is_active=True).count(),
    }
    
    # Recent work items
    recent_work_items = WorkItem.objects.filter(
        workflow__organization=organization
    ).select_related(
        'workflow', 'current_step', 'current_assignee__user', 'created_by__user'
    ).order_by('-updated_at')[:10]
    
    # Upcoming bookings for user's teams
    user_teams = profile.teams.filter(is_active=True)
    upcoming_bookings = TeamBooking.objects.filter(
        team__in=user_teams,
        start_time__gte=timezone.now(),
        is_completed=False
    ).select_related(
        'team', 'work_item', 'job_type', 'booked_by__user'
    ).order_by('start_time')[:5]
    
    context = {
        'profile': profile,
        'organization': organization,
        'stats': stats,
        'recent_work_items': recent_work_items,
        'upcoming_bookings': upcoming_bookings,
    }
    
    return render(request, 'cflows/dashboard.html', context)


@login_required
def workflows_list(request):
    """List workflows for the user's organization"""
    profile = get_user_profile(request)
    
    if not profile:
        return render(request, 'cflows/no_profile.html')
    
    workflows = Workflow.objects.filter(
        organization=profile.organization,
        is_active=True
    ).select_related('created_by__user').annotate(
        step_count=Count('steps'),
        work_item_count=Count('work_items')
    ).order_by('name')
    
    # Pagination
    paginator = Paginator(workflows, 12)  # Show 12 workflows per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'profile': profile,
        'page_obj': page_obj,
        'workflows': page_obj,
    }
    
    return render(request, 'cflows/workflows_list.html', context)


@login_required
def create_workflow(request):
    """Create new workflow - placeholder for now"""
    profile = get_user_profile(request)
    
    if not profile:
        return render(request, 'cflows/no_profile.html')
    
    # This would be replaced with a proper form
    if request.method == 'POST':
        messages.info(request, "Workflow creation form will be implemented next!")
        return redirect('cflows:workflows_list')
    
    context = {
        'profile': profile,
    }
    
    return render(request, 'cflows/create_workflow.html', context)


@login_required
def workflow_detail(request, pk):
    """Workflow detail view"""
    profile = get_user_profile(request)
    
    if not profile:
        return render(request, 'cflows/no_profile.html')
    
    workflow = get_object_or_404(
        Workflow.objects.select_related('organization', 'created_by__user'),
        pk=pk,
        organization=profile.organization
    )
    
    # Get workflow steps with transition information
    steps = WorkflowStep.objects.filter(workflow=workflow).select_related(
        'assigned_team'
    ).prefetch_related(
        'outgoing_transitions__to_step',
        'incoming_transitions__from_step'
    ).order_by('order')
    
    # Get work items for this workflow
    work_items = WorkItem.objects.filter(workflow=workflow).select_related(
        'current_step', 'current_assignee__user', 'created_by__user'
    ).order_by('-updated_at')
    
    # Pagination for work items
    paginator = Paginator(work_items, 20)
    page_number = request.GET.get('page')
    work_items_page = paginator.get_page(page_number)
    
    context = {
        'profile': profile,
        'workflow': workflow,
        'steps': steps,
        'work_items': work_items_page,
    }
    
    return render(request, 'cflows/workflow_detail.html', context)


@login_required
def work_items_list(request):
    """List work items with filtering"""
    profile = get_user_profile(request)
    
    if not profile:
        return render(request, 'cflows/no_profile.html')
    
    # Base queryset
    work_items = WorkItem.objects.filter(
        workflow__organization=profile.organization
    ).select_related(
        'workflow', 'current_step', 'current_assignee__user', 'created_by__user'
    )
    
    # Filtering
    workflow_id = request.GET.get('workflow')
    if workflow_id:
        work_items = work_items.filter(workflow_id=workflow_id)
    
    status_filter = request.GET.get('status')
    if status_filter == 'completed':
        work_items = work_items.filter(is_completed=True)
    elif status_filter == 'active':
        work_items = work_items.filter(is_completed=False)
    
    assignee_filter = request.GET.get('assignee')
    if assignee_filter == 'me':
        work_items = work_items.filter(current_assignee=profile)
    elif assignee_filter == 'unassigned':
        work_items = work_items.filter(current_assignee=None)
    
    # Search
    search = request.GET.get('search')
    if search:
        work_items = work_items.filter(
            Q(title__icontains=search) | 
            Q(description__icontains=search)
        )
    
    work_items = work_items.order_by('-updated_at')
    
    # Pagination
    paginator = Paginator(work_items, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get workflows for filter dropdown
    workflows = Workflow.objects.filter(
        organization=profile.organization, is_active=True
    ).order_by('name')
    
    context = {
        'profile': profile,
        'page_obj': page_obj,
        'work_items': page_obj,
        'workflows': workflows,
        'current_filters': {
            'workflow': workflow_id,
            'status': status_filter,
            'assignee': assignee_filter,
            'search': search,
        }
    }
    
    return render(request, 'cflows/work_items_list.html', context)


@login_required
def work_item_detail(request, uuid):
    """Work item detail view"""
    profile = get_user_profile(request)
    
    if not profile:
        return render(request, 'cflows/no_profile.html')
    
    work_item = get_object_or_404(
        WorkItem.objects.select_related(
            'workflow', 'current_step', 'current_assignee__user', 'created_by__user'
        ),
        uuid=uuid,
        workflow__organization=profile.organization
    )
    
    # Get history
    history = WorkItemHistory.objects.filter(work_item=work_item).select_related(
        'from_step', 'to_step', 'changed_by__user'
    ).order_by('-created_at')
    
    # Get available transitions from current step
    available_transitions = WorkflowTransition.objects.filter(
        from_step=work_item.current_step
    ).select_related('to_step')
    
    # Get related bookings
    bookings = TeamBooking.objects.filter(work_item=work_item).select_related(
        'team', 'job_type', 'booked_by__user', 'completed_by__user'
    ).order_by('-start_time')
    
    context = {
        'profile': profile,
        'work_item': work_item,
        'history': history,
        'available_transitions': available_transitions,
        'bookings': bookings,
    }
    
    return render(request, 'cflows/work_item_detail.html', context)


@login_required
@require_business_organization
def team_bookings_list(request):
    """List team bookings"""
    profile = request.user.mediap_profile
    
    if not profile:
        return render(request, 'cflows/no_profile.html')
    
    # Get user's teams
    user_teams = profile.teams.filter(is_active=True)
    
    # Base queryset - bookings for user's teams
    bookings = TeamBooking.objects.filter(
        team__in=user_teams
    ).select_related(
        'team', 'work_item', 'job_type', 'booked_by__user', 'completed_by__user'
    )
    
    # Filtering
    team_id = request.GET.get('team')
    if team_id:
        bookings = bookings.filter(team_id=team_id)
    
    status_filter = request.GET.get('status')
    if status_filter == 'completed':
        bookings = bookings.filter(is_completed=True)
    elif status_filter == 'upcoming':
        bookings = bookings.filter(is_completed=False, start_time__gte=timezone.now())
    elif status_filter == 'active':
        bookings = bookings.filter(is_completed=False)
    
    bookings = bookings.order_by('-start_time')
    
    # Pagination
    paginator = Paginator(bookings, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'profile': profile,
        'page_obj': page_obj,
        'bookings': page_obj,
        'user_teams': user_teams,
        'current_filters': {
            'team': team_id,
            'status': status_filter,
        }
    }
    
    return render(request, 'cflows/team_bookings_list.html', context)


@login_required
def calendar_view(request):
    """Calendar view with events and bookings"""
    profile = get_user_profile(request)
    
    if not profile:
        return render(request, 'cflows/no_profile.html')
    
    # This would integrate with FullCalendar.js
    # For now, just show a placeholder
    
    context = {
        'profile': profile,
        'organization': profile.organization,
    }
    
    return render(request, 'cflows/calendar.html', context)
