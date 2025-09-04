from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Prefetch, Case, When, IntegerField
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods
from django.db import transaction
from core.models import Organization, UserProfile, Team, JobType, CalendarEvent
from core.views import require_organization_access, require_business_organization
from .models import (
    Workflow, WorkflowStep, WorkflowTransition, WorkflowTemplate,
    WorkItem, WorkItemHistory, WorkItemComment, WorkItemAttachment,
    WorkItemRevision, TeamBooking
)
from .forms import (
    WorkflowForm, WorkflowStepForm, WorkItemForm, WorkItemCommentForm,
    WorkItemAttachmentForm, WorkflowTransitionForm, TeamBookingForm
)
import json


def apply_workflow_template(workflow):
    """Apply template structure to a workflow"""
    if not workflow.template or not workflow.template.template_data:
        return
    
    template_data = workflow.template.template_data
    steps_data = template_data.get('steps', [])
    transitions_data = template_data.get('transitions', [])
    
    # Create steps
    step_mapping = {}
    for step_data in steps_data:
        step = WorkflowStep.objects.create(
            workflow=workflow,
            name=step_data['name'],
            description=step_data.get('description', ''),
            order=step_data.get('order', 1),
            requires_booking=step_data.get('requires_booking', False),
            estimated_duration_hours=step_data.get('estimated_duration_hours'),
            is_terminal=step_data.get('is_terminal', False),
            data_schema=step_data.get('data_schema', {})
        )
        step_mapping[step_data['id']] = step
    
    # Create transitions
    for transition_data in transitions_data:
        from_step = step_mapping.get(transition_data['from_step_id'])
        to_step = step_mapping.get(transition_data['to_step_id'])
        
        if from_step and to_step:
            WorkflowTransition.objects.create(
                from_step=from_step,
                to_step=to_step,
                label=transition_data.get('label', ''),
                condition=transition_data.get('condition', {})
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
@require_organization_access
def create_workflow(request):
    """Create new workflow with enhanced form"""
    profile = get_user_profile(request)
    
    if not profile:
        return render(request, 'cflows/no_profile.html')
    
    if request.method == 'POST':
        form = WorkflowForm(request.POST, organization=profile.organization)
        if form.is_valid():
            workflow = form.save(commit=False)
            workflow.organization = profile.organization
            workflow.created_by = profile
            workflow.save()
            
            # If created from template, apply template structure
            if workflow.template:
                apply_workflow_template(workflow)
            
            messages.success(request, f'Workflow "{workflow.name}" created successfully!')
            return redirect('cflows:workflow_detail', workflow_id=workflow.id)
    else:
        form = WorkflowForm(organization=profile.organization)
    
    # Get available templates
    templates = WorkflowTemplate.objects.filter(
        Q(is_public=True) | Q(created_by_org=profile.organization)
    ).order_by('category', 'name')
    
    context = {
        'profile': profile,
        'form': form,
        'templates': templates,
    }
    
    return render(request, 'cflows/create_workflow.html', context)


@login_required
@require_organization_access
def workflow_detail(request, workflow_id):
    """Detailed view of a workflow with steps and statistics"""
    profile = get_user_profile(request)
    if not profile:
        return render(request, 'cflows/no_profile.html')
    
    workflow = get_object_or_404(
        Workflow.objects.select_related('created_by__user', 'template'),
        id=workflow_id,
        organization=profile.organization
    )
    
    # Get workflow steps with transitions
    steps = workflow.steps.prefetch_related(
        'outgoing_transitions__to_step',
        'incoming_transitions__from_step'
    ).order_by('order')
    
    # Statistics
    stats = {
        'total_items': workflow.work_items.count(),
        'active_items': workflow.work_items.filter(is_completed=False).count(),
        'completed_items': workflow.work_items.filter(is_completed=True).count(),
        'steps_count': steps.count(),
    }
    
    # Recent work items
    recent_items = workflow.work_items.select_related(
        'current_step', 'current_assignee__user', 'created_by__user'
    ).order_by('-updated_at')[:10]
    
    context = {
        'profile': profile,
        'workflow': workflow,
        'steps': steps,
        'stats': stats,
        'recent_items': recent_items,
    }
    
    return render(request, 'cflows/workflow_detail.html', context)


@login_required
@require_organization_access
def work_items_list(request):
    """Enhanced work items list with filtering and search"""
    profile = get_user_profile(request)
    if not profile:
        return render(request, 'cflows/no_profile.html')
    
    # Check if this is an API request
    is_api = request.GET.get('api') == 'true'
    
    # Base queryset
    work_items = WorkItem.objects.filter(
        workflow__organization=profile.organization
    ).select_related(
        'workflow', 'current_step', 'current_assignee__user', 'created_by__user'
    ).prefetch_related('attachments', 'comments')
    
    # Filtering
    workflow_id = request.GET.get('workflow')
    if workflow_id:
        work_items = work_items.filter(workflow_id=workflow_id)
    
    assignee_id = request.GET.get('assignee')
    if assignee_id:
        work_items = work_items.filter(current_assignee_id=assignee_id)
    
    priority = request.GET.get('priority')
    if priority:
        work_items = work_items.filter(priority=priority)
    
    status = request.GET.get('status')
    if status == 'active':
        work_items = work_items.filter(is_completed=False)
    elif status == 'completed':
        work_items = work_items.filter(is_completed=True)
    
    # Search
    search = request.GET.get('search')
    if search:
        work_items = work_items.filter(
            Q(title__icontains=search) | 
            Q(description__icontains=search) |
            Q(tags__contains=[search])
        )
    
    # Sorting
    sort = request.GET.get('sort', '-updated_at')
    if sort in ['-updated_at', 'updated_at', 'title', '-title', 'priority', '-priority', 'due_date', '-due_date']:
        work_items = work_items.order_by(sort)
    
    # Pagination
    paginator = Paginator(work_items, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # For API requests, return JSON
    if is_api:
        work_items_data = []
        for item in page_obj.object_list:
            work_items_data.append({
                'id': item.id,
                'title': item.title,
                'workflow': item.workflow.name,
                'priority': item.priority,
                'current_step': item.current_step.name if item.current_step else 'Unknown',
                'assigned_to': item.current_assignee.user.get_full_name() if item.current_assignee and item.current_assignee.user else None,
                'due_date': item.due_date.isoformat() if item.due_date else None,
                'created_at': item.created_at.isoformat(),
                'completed': item.is_completed
            })
        
        return JsonResponse({
            'success': True,
            'work_items': work_items_data,
            'total_count': paginator.count,
            'page_count': paginator.num_pages
        })
    
    # Get filter options
    workflows = Workflow.objects.filter(
        organization=profile.organization, is_active=True
    ).order_by('name')
    
    assignees = UserProfile.objects.filter(
        organization=profile.organization, user__is_active=True
    ).order_by('user__first_name', 'user__last_name')
    
    context = {
        'profile': profile,
        'page_obj': page_obj,
        'workflows': workflows,
        'assignees': assignees,
        'current_filters': {
            'workflow': workflow_id,
            'assignee': assignee_id,
            'priority': priority,
            'status': status,
            'search': search,
            'sort': sort,
        }
    }
    
    return render(request, 'cflows/work_items_list.html', context)


@login_required
@require_organization_access
def create_work_item(request, workflow_id):
    """Create a new work item in a workflow"""
    profile = get_user_profile(request)
    if not profile:
        return render(request, 'cflows/no_profile.html')
    
    workflow = get_object_or_404(
        Workflow,
        id=workflow_id,
        organization=profile.organization,
        is_active=True
    )
    
    # Get the first step of the workflow
    first_step = workflow.steps.order_by('order').first()
    if not first_step:
        messages.error(request, 'This workflow has no steps defined.')
        return redirect('cflows:workflow_detail', workflow_id=workflow.id)
    
    if request.method == 'POST':
        form = WorkItemForm(request.POST, organization=profile.organization, workflow=workflow)
        if form.is_valid():
            work_item = form.save(commit=False)
            work_item.workflow = workflow
            work_item.current_step = first_step
            work_item.created_by = profile
            work_item.save()
            
            # Save custom fields after the work item is saved
            form.save_custom_fields(work_item)
            
            # Create initial history entry
            WorkItemHistory.objects.create(
                work_item=work_item,
                to_step=first_step,
                changed_by=profile,
                notes="Work item created",
                data_snapshot=work_item.data
            )
            
            # Create revision
            WorkItemRevision.objects.create(
                work_item=work_item,
                revision_number=1,
                title=work_item.title,
                description=work_item.description,
                rich_content=work_item.rich_content,
                data=work_item.data,
                changed_by=profile,
                change_summary="Initial creation"
            )
            
            messages.success(request, f'Work item "{work_item.title}" created successfully!')
            return redirect('cflows:work_item_detail', work_item_id=work_item.id)
        else:
            # Log form errors for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"WorkItem form validation failed: {form.errors}")
            messages.error(request, 'Please correct the errors below.')
    else:
        form = WorkItemForm(organization=profile.organization, workflow=workflow)
    
    # Get custom fields for template display
    from .models import CustomField
    custom_fields = []
    if profile.organization:
        custom_field_objects = CustomField.objects.filter(
            organization=profile.organization,
            is_active=True
        ).filter(
            Q(workflows__isnull=True) | Q(workflows=workflow)
        ).order_by('section', 'order', 'label')
        
        for cf in custom_field_objects:
            field_name = f'custom_{cf.id}'
            if field_name in form.fields:
                custom_fields.append({
                    'field': form[field_name],
                    'section': cf.section or '',
                    'custom_field': cf
                })
    
    context = {
        'profile': profile,
        'workflow': workflow,
        'form': form,
        'custom_fields': custom_fields,
    }
    
    return render(request, 'cflows/create_work_item.html', context)


@login_required
@require_organization_access
def work_item_detail(request, work_item_id):
    """Detailed view of a work item with comments, attachments, and history"""
    profile = get_user_profile(request)
    if not profile:
        return render(request, 'cflows/no_profile.html')
    
    work_item = get_object_or_404(
        WorkItem.objects.select_related(
            'workflow', 'current_step', 'current_assignee__user', 'created_by__user'
        ).prefetch_related(
            'attachments__uploaded_by__user',
            'comments__author__user',
            'history__from_step',
            'history__to_step',
            'history__changed_by__user',
            'depends_on',
            'dependents',
            'watchers__user'
        ),
        id=work_item_id,
        workflow__organization=profile.organization
    )
    
    # Available transitions from current step
    available_transitions = work_item.current_step.outgoing_transitions.select_related('to_step')
    
    # Handle comment form
    comment_form = None
    if request.method == 'POST':
        if 'add_comment' in request.POST:
            comment_form = WorkItemCommentForm(request.POST)
            if comment_form.is_valid():
                comment = comment_form.save(commit=False)
                comment.work_item = work_item
                comment.author = profile
                comment.save()
                messages.success(request, 'Comment added successfully!')
                return redirect('cflows:work_item_detail', work_item_id=work_item.id)
    
    if not comment_form:
        comment_form = WorkItemCommentForm()
    
    # Get comments in thread order
    comments = work_item.comments.filter(parent=None).order_by('created_at')
    
    # Get history
    history = work_item.history.order_by('-created_at')
    
    context = {
        'profile': profile,
        'work_item': work_item,
        'available_transitions': available_transitions,
        'comment_form': comment_form,
        'comments': comments,
        'history': history,
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
        'team', 'work_item', 'job_type', 'booked_by', 'completed_by'
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
    
    # Date filtering
    date_from = request.GET.get('date_from')
    if date_from:
        bookings = bookings.filter(start_time__gte=date_from)
    
    date_to = request.GET.get('date_to')
    if date_to:
        bookings = bookings.filter(end_time__lte=date_to)
    
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
            'date_from': date_from,
            'date_to': date_to,
        }
    }
    
    return render(request, 'cflows/team_bookings_list.html', context)


@login_required
@require_business_organization
@require_http_methods(["POST"])
def complete_booking(request, booking_id):
    """Complete a team booking"""
    try:
        profile = request.user.mediap_profile
        booking = get_object_or_404(TeamBooking, id=booking_id, team__members=profile)
        
        if booking.is_completed:
            return JsonResponse({'success': False, 'error': 'Booking is already completed'})
        
        booking.is_completed = True
        booking.completed_at = timezone.now()
        booking.completed_by = profile
        booking.save()
        
        # If linked to workflow step, progress the work item
        if booking.work_item and booking.workflow_step:
            # This could trigger workflow progression logic
            pass
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


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
