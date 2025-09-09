from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Prefetch, Case, When, IntegerField
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods
from django.db import transaction, models
from core.models import Organization, UserProfile, Team, JobType, CalendarEvent
from core.views import require_organization_access, require_business_organization
from core.decorators import require_permission
from .models import (
    Workflow, WorkflowStep, WorkflowTransition, WorkflowTemplate,
    WorkItem, WorkItemHistory, WorkItemComment, WorkItemAttachment,
    WorkItemRevision, TeamBooking, CustomField, WorkItemCustomFieldValue
)
from .forms import (
    WorkflowForm, WorkflowStepForm, WorkItemForm, WorkItemCommentForm,
    WorkItemAttachmentForm, WorkflowTransitionForm, TeamBookingForm,
    CustomFieldForm, TeamForm, WorkflowCreationForm, BulkTransitionForm,
    WorkflowFieldConfigForm
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
@login_required
@require_organization_access
@require_permission('workflow.create')
def create_workflow(request):
    """Create new workflow with enhanced form"""
    profile = get_user_profile(request)
    
    if not profile:
        return render(request, 'cflows/no_profile.html')
    
    if request.method == 'POST':
        form = WorkflowForm(request.POST, organization=profile.organization, user_profile=profile)
        if form.is_valid():
            workflow = form.save(commit=False)
            workflow.organization = profile.organization
            workflow.created_by = profile
            workflow.save()
            
            # Save many-to-many fields
            form.save_m2m()
            
            # If created from template, apply template structure
            if workflow.template:
                apply_workflow_template(workflow)
            
            messages.success(request, f'Workflow "{workflow.name}" created successfully!')
            return redirect('cflows:workflow_detail', workflow_id=workflow.id)
    else:
        form = WorkflowForm(organization=profile.organization, user_profile=profile)
    
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
@login_required
@require_organization_access
@require_permission('workflow.view')
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
@require_permission('workflow.configure')
def workflow_field_config(request, workflow_id):
    """Configure which fields are shown/hidden/replaced for work items in this workflow"""
    profile = get_user_profile(request)
    if not profile or not profile.organization:
        return redirect('cflows:index')
    
    workflow = get_object_or_404(
        Workflow,
        id=workflow_id,
        organization=profile.organization
    )
    
    # Check permissions
    if not (profile.is_organization_admin or profile.has_staff_panel_access):
        messages.error(request, "You don't have permission to configure workflow fields.")
        return redirect('cflows:workflow_detail', workflow_id=workflow_id)
    
    if request.method == 'POST':
        form = WorkflowFieldConfigForm(
            request.POST,
            workflow=workflow,
            organization=profile.organization
        )
        if form.is_valid():
            config = form.save_config()
            messages.success(request, f"Field configuration saved successfully for {workflow.name}")
            return redirect('cflows:workflow_detail', workflow_id=workflow_id)
    else:
        form = WorkflowFieldConfigForm(
            workflow=workflow,
            organization=profile.organization
        )
    
    # Get current configuration for display
    current_config = workflow.get_active_fields()
    
    context = {
        'profile': profile,
        'organization': profile.organization,
        'workflow': workflow,
        'form': form,
        'current_config': current_config,
        'title': f'Configure Fields - {workflow.name}'
    }
    
    return render(request, 'cflows/workflow_field_config.html', context)


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
    if workflow_id and workflow_id.strip():
        work_items = work_items.filter(workflow_id=workflow_id)
    
    assignee_id = request.GET.get('assignee')
    if assignee_id and assignee_id.strip():
        work_items = work_items.filter(current_assignee_id=assignee_id)
    
    priority = request.GET.get('priority')
    if priority and priority.strip():
        work_items = work_items.filter(priority=priority)
    
    status = request.GET.get('status')
    if status and status.strip():
        if status == 'active':
            work_items = work_items.filter(is_completed=False)
        elif status == 'completed':
            work_items = work_items.filter(is_completed=True)
    
    # Search
    search = request.GET.get('search')
    if search and search.strip() and search.lower() != 'none':
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
            'workflow': workflow_id if workflow_id and workflow_id.strip() else '',
            'assignee': assignee_id if assignee_id and assignee_id.strip() else '',
            'priority': priority if priority and priority.strip() else '',
            'status': status if status and status.strip() else '',
            'search': search if search and search.strip() and search.lower() != 'none' else '',
            'sort': sort,
        }
    }
    
    return render(request, 'cflows/work_items_list.html', context)


@login_required
@require_organization_access
@login_required
@require_organization_access
@require_permission('workitem.create')
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
def create_work_item_select_workflow(request):
    """Select workflow step for creating a new work item"""
    profile = get_user_profile(request)
    if not profile:
        return render(request, 'cflows/no_profile.html')
    
    if request.method == 'POST':
        workflow_id = request.POST.get('workflow_id')
        if workflow_id:
            return redirect('cflows:create_work_item', workflow_id=workflow_id)
        else:
            messages.error(request, 'Please select a workflow.')
    
    # Get active workflows for the organization
    workflows = Workflow.objects.filter(
        organization=profile.organization,
        is_active=True
    ).order_by('name')
    
    if not workflows.exists():
        messages.error(request, 'No active workflows found. Create a workflow first.')
        return redirect('cflows:workflow_list')
    
    # If only one workflow, go directly to work item creation
    if workflows.count() == 1:
        return redirect('cflows:create_work_item', workflow_id=workflows.first().id)
    
    context = {
        'profile': profile,
        'organization': profile.organization,
        'workflows': workflows,
    }
    
    return render(request, 'cflows/create_work_item_select_workflow.html', context)


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
    
    # Backward transition support
    can_move_backward = work_item.can_move_backward(profile)
    backward_steps = work_item.get_available_backward_steps() if can_move_backward else None
    
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

    # Booking gating / status context
    booking_status = None
    if work_item.current_step and work_item.current_step.requires_booking:
        from services.cflows.models import TeamBooking  # local import to avoid circulars
        step_bookings = TeamBooking.objects.filter(work_item=work_item, workflow_step=work_item.current_step)
        total = step_bookings.count()
        completed = step_bookings.filter(is_completed=True).count()
        remaining = total - completed
        booking_status = {
            'required': True,
            'total': total,
            'completed': completed,
            'remaining': remaining,
            'all_completed': total > 0 and remaining == 0,
            'has_any': total > 0,
            'needs_creation': total == 0,
        }
    else:
        booking_status = {'required': False}
    
    context = {
        'profile': profile,
        'work_item': work_item,
        'available_transitions': available_transitions,
        'can_move_backward': can_move_backward,
        'backward_steps': backward_steps,
        'comment_form': comment_form,
        'comments': comments,
        'history': history,
    'booking_status': booking_status,
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

        if(
            booking.source_service == 'cflows' and
            booking.source_object_type.lower() == 'teambooking'
        ):
            from .integrations import get_service_integrations  # local import to avoid circulars
            integration = get_service_integrations(booking.organization)
            integration.mark_completed(request, [booking])

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


# Custom Fields Management Views

@login_required
@require_business_organization
def custom_fields_list(request):
    """List all custom fields for the organization"""
    profile = get_user_profile(request)
    if not profile or not profile.organization:
        return redirect('cflows:index')
    
    # Check if user is org admin
    if not profile.is_organization_admin:
        messages.error(request, "Only organization admins can manage custom fields.")
        return redirect('cflows:index')
    
    # Get custom fields
    custom_fields = CustomField.objects.filter(
        organization=profile.organization
    ).prefetch_related('workflows', 'workflow_steps').order_by('section', 'order', 'label')
    
    context = {
        'profile': profile,
        'organization': profile.organization,
        'custom_fields': custom_fields,
    }
    
    return render(request, 'cflows/custom_fields_list.html', context)


@login_required
@require_business_organization
@require_permission('customfields.manage')
def create_custom_field(request):
    """Create a new custom field"""
    profile = get_user_profile(request)
    if not profile or not profile.organization:
        return redirect('cflows:index')
    
    # Check if user is org admin
    if not profile.is_organization_admin:
        messages.error(request, "Only organization admins can manage custom fields.")
        return redirect('cflows:index')
    
    if request.method == 'POST':
        form = CustomFieldForm(request.POST, organization=profile.organization)
        if form.is_valid():
            custom_field = form.save(commit=False)
            custom_field.organization = profile.organization
            custom_field.save()
            form.save_m2m()  # Save many-to-many relationships
            messages.success(request, f"Custom field '{custom_field.label}' created successfully.")
            return redirect('cflows:custom_fields_list')
    else:
        form = CustomFieldForm(organization=profile.organization)
    
    context = {
        'profile': profile,
        'organization': profile.organization,
        'form': form,
        'title': 'Create Custom Field'
    }
    
    return render(request, 'cflows/custom_field_form.html', context)


@login_required
@require_business_organization
@require_permission('customfields.manage')
def edit_custom_field(request, field_id):
    """Edit an existing custom field"""
    profile = get_user_profile(request)
    if not profile or not profile.organization:
        return redirect('cflows:index')
    
    # Check if user is org admin
    if not profile.is_organization_admin:
        messages.error(request, "Only organization admins can manage custom fields.")
        return redirect('cflows:index')
    
    custom_field = get_object_or_404(
        CustomField,
        id=field_id,
        organization=profile.organization
    )
    
    if request.method == 'POST':
        form = CustomFieldForm(request.POST, instance=custom_field, organization=profile.organization)
        if form.is_valid():
            form.save()
            messages.success(request, f"Custom field '{custom_field.label}' updated successfully.")
            return redirect('cflows:custom_fields_list')
    else:
        form = CustomFieldForm(instance=custom_field, organization=profile.organization)
    
    context = {
        'profile': profile,
        'organization': profile.organization,
        'form': form,
        'custom_field': custom_field,
        'title': 'Edit Custom Field'
    }
    
    return render(request, 'cflows/custom_field_form.html', context)


@login_required
@require_business_organization
@require_POST
@require_permission('customfields.manage')
def delete_custom_field(request, field_id):
    """Delete a custom field"""
    profile = get_user_profile(request)
    if not profile or not profile.organization:
        return redirect('cflows:index')
    
    # Check if user is org admin
    if not profile.is_organization_admin:
        messages.error(request, "Only organization admins can manage custom fields.")
        return redirect('cflows:index')
    
    custom_field = get_object_or_404(
        CustomField,
        id=field_id,
        organization=profile.organization
    )
    
    # Check if field has any values
    value_count = WorkItemCustomFieldValue.objects.filter(custom_field=custom_field).count()
    
    if value_count > 0:
        messages.warning(
            request, 
            f"Custom field '{custom_field.label}' has {value_count} values and cannot be deleted. "
            "You can deactivate it instead."
        )
    else:
        field_label = custom_field.label
        custom_field.delete()
        messages.success(request, f"Custom field '{field_label}' deleted successfully.")
    
    return redirect('cflows:custom_fields_list')


@login_required
@require_business_organization
@require_POST  
def toggle_custom_field(request, field_id):
    """Toggle active status of a custom field"""
    profile = get_user_profile(request)
    if not profile or not profile.organization:
        return redirect('cflows:index')
    
    # Check if user is org admin
    if not profile.is_organization_admin:
        messages.error(request, "Only organization admins can manage custom fields.")
        return redirect('cflows:index')
    
    custom_field = get_object_or_404(
        CustomField,
        id=field_id,
        organization=profile.organization
    )
    
    custom_field.is_active = not custom_field.is_active
    custom_field.save()
    
    status = "activated" if custom_field.is_active else "deactivated"
    messages.success(request, f"Custom field '{custom_field.label}' {status}.")
    
    return redirect('cflows:custom_fields_list')


# Team Management Views

@login_required
@require_business_organization
def teams_list(request):
    """List all teams for the organization"""
    profile = get_user_profile(request)
    if not profile or not profile.organization:
        return redirect('cflows:index')
    
    # Check if user is org admin or has staff access
    if not (profile.is_organization_admin or profile.has_staff_panel_access):
        messages.error(request, "You don't have permission to manage teams.")
        return redirect('cflows:index')
    
    # Get teams with member count, organized by hierarchy
    all_teams = Team.objects.filter(
        organization=profile.organization
    ).prefetch_related('members__user', 'sub_teams').annotate(
        members_count=models.Count('members')
    ).order_by('name')
    
    # Separate top-level teams and organize into hierarchy
    top_level_teams = all_teams.filter(parent_team__isnull=True)
    
    # Create a hierarchical structure for display
    def build_team_hierarchy(team):
        team_data = {
            'team': team,
            'sub_teams': []
        }
        for sub_team in team.sub_teams.all():
            team_data['sub_teams'].append(build_team_hierarchy(sub_team))
        return team_data
    
    hierarchical_teams = [build_team_hierarchy(team) for team in top_level_teams]
    
    context = {
        'profile': profile,
        'organization': profile.organization,
        'teams': all_teams,  # Keep for backward compatibility
        'hierarchical_teams': hierarchical_teams,
        'total_teams': all_teams.count(),
        'top_level_teams_count': top_level_teams.count(),
    }
    
    return render(request, 'cflows/teams_list.html', context)


@login_required
@require_business_organization
@require_permission('team.create')
def create_team(request):
    """Create a new team"""
    profile = get_user_profile(request)
    if not profile or not profile.organization:
        return redirect('cflows:index')
    
    # Check if user is org admin or has staff access
    if not (profile.is_organization_admin or profile.has_staff_panel_access):
        messages.error(request, "You don't have permission to create teams.")
        return redirect('cflows:index')
    
    # Get parent team if specified
    parent_team_id = request.GET.get('parent')
    parent_team = None
    if parent_team_id:
        try:
            parent_team = Team.objects.get(
                id=parent_team_id,
                organization=profile.organization
            )
        except Team.DoesNotExist:
            messages.error(request, "Parent team not found.")
            return redirect('cflows:teams_list')
    
    if request.method == 'POST':
        form = TeamForm(request.POST, organization=profile.organization)
        if form.is_valid():
            team = form.save(commit=False)
            team.organization = profile.organization
            team.created_by = profile
            team.save()
            
            team_type = "sub-team" if team.parent_team else "team"
            messages.success(request, f"{team_type.title()} '{team.name}' created successfully!")
            return redirect('cflows:teams_list')
    else:
        initial_data = {}
        if parent_team:
            initial_data['parent_team'] = parent_team
        form = TeamForm(organization=profile.organization, initial=initial_data)
    
    context = {
        'profile': profile,
        'organization': profile.organization,
        'form': form,
        'parent_team': parent_team,
        'title': f'Create {"Sub-team" if parent_team else "Team"}' + (f' under {parent_team.name}' if parent_team else '')
    }
    
    return render(request, 'cflows/team_form.html', context)


@login_required
@require_business_organization
@require_permission('team.edit')
def edit_team(request, team_id):
    """Edit an existing team"""
    profile = get_user_profile(request)
    if not profile or not profile.organization:
        return redirect('cflows:index')
    
    # Check if user is org admin or has staff access
    if not (profile.is_organization_admin or profile.has_staff_panel_access):
        messages.error(request, "You don't have permission to edit teams.")
        return redirect('cflows:index')
    
    team = get_object_or_404(
        Team,
        id=team_id,
        organization=profile.organization
    )
    
    if request.method == 'POST':
        form = TeamForm(request.POST, instance=team, organization=profile.organization, current_team=team)
        if form.is_valid():
            form.save()
            messages.success(request, f"Team '{team.name}' updated successfully!")
            return redirect('cflows:teams_list')
    else:
        form = TeamForm(instance=team, organization=profile.organization, current_team=team)
    
    context = {
        'profile': profile,
        'organization': profile.organization,
        'form': form,
        'team': team,
        'title': f'Edit Team: {team.name}'
    }
    
    return render(request, 'cflows/team_form.html', context)


@login_required
@require_business_organization
def team_detail(request, team_id):
    """Detailed view of a team with member management"""
    profile = get_user_profile(request)
    if not profile or not profile.organization:
        return redirect('cflows:index')
    
    team = get_object_or_404(
        Team,
        id=team_id,
        organization=profile.organization
    )
    
    # Get team members
    team_members = team.members.select_related('user').order_by('user__first_name', 'user__last_name')
    
    # Get available users to add to team (org members not already in team)
    available_users = UserProfile.objects.filter(
        organization=profile.organization,
        user__is_active=True
    ).exclude(
        id__in=team_members.values_list('id', flat=True)
    ).select_related('user').order_by('user__first_name', 'user__last_name')
    
    # Handle adding/removing team members
    if request.method == 'POST':
        if 'add_member' in request.POST:
            user_id = request.POST.get('user_id')
            if user_id:
                try:
                    user_profile = UserProfile.objects.get(
                        id=user_id,
                        organization=profile.organization,
                        user__is_active=True
                    )
                    team.members.add(user_profile)
                    messages.success(request, f"Added {user_profile.user.get_full_name() or user_profile.user.username} to the team.")
                except UserProfile.DoesNotExist:
                    messages.error(request, "User not found.")
            return redirect('cflows:team_detail', team_id=team.id)
        
        elif 'remove_member' in request.POST:
            user_id = request.POST.get('user_id')
            if user_id:
                try:
                    user_profile = UserProfile.objects.get(
                        id=user_id,
                        organization=profile.organization
                    )
                    team.members.remove(user_profile)
                    messages.success(request, f"Removed {user_profile.user.get_full_name() or user_profile.user.username} from the team.")
                except UserProfile.DoesNotExist:
                    messages.error(request, "User not found.")
            return redirect('cflows:team_detail', team_id=team.id)
    
    # Get team statistics
    from .models import TeamBooking
    stats = {
        'total_bookings': TeamBooking.objects.filter(team=team).count(),
        'active_bookings': TeamBooking.objects.filter(team=team, is_completed=False).count(),
        'completed_bookings': TeamBooking.objects.filter(team=team, is_completed=True).count(),
        'member_count': team_members.count(),
    }
    
    context = {
        'profile': profile,
        'organization': profile.organization,
        'team': team,
        'team_members': team_members,
        'available_users': available_users,
        'stats': stats,
        'can_manage': profile.is_organization_admin or profile.has_staff_panel_access,
    }
    
    return render(request, 'cflows/team_detail.html', context)


@login_required
@require_business_organization
def create_workflow_enhanced(request):
    """Enhanced workflow creation with step creation"""
    profile = get_user_profile(request)
    if not profile or not profile.organization:
        return redirect('cflows:index')
    
    # Check if user is org admin or has staff access
    if not (profile.is_organization_admin or profile.has_staff_panel_access):
        messages.error(request, "You don't have permission to create workflows.")
        return redirect('cflows:index')
    
    if request.method == 'POST':
        form = WorkflowCreationForm(request.POST, organization=profile.organization)
        if form.is_valid():
            workflow = form.save(commit=True, created_by=profile)
            messages.success(request, f"Workflow '{workflow.name}' created successfully with {workflow.steps.count()} steps!")
            return redirect('cflows:workflow_detail', workflow_id=workflow.id)
    else:
        form = WorkflowCreationForm(organization=profile.organization)
    
    # Get available teams for step assignment
    teams = Team.objects.filter(
        organization=profile.organization,
        is_active=True
    ).order_by('name')
    
    context = {
        'profile': profile,
        'organization': profile.organization,
        'form': form,
        'teams': teams,
        'title': 'Create New Workflow'
    }
    
    return render(request, 'cflows/create_workflow_enhanced.html', context)


@login_required
@require_business_organization
def workflow_transitions_manager(request, workflow_id):
    """Visual workflow transition manager"""
    profile = get_user_profile(request)
    if not profile or not profile.organization:
        return redirect('cflows:index')
    
    workflow = get_object_or_404(
        Workflow, 
        id=workflow_id, 
        organization=profile.organization
    )
    
    # Check permissions
    if not (profile.is_organization_admin or profile.has_staff_panel_access):
        messages.error(request, "You don't have permission to manage workflow transitions.")
        return redirect('cflows:workflow_detail', workflow_id=workflow_id)
    
    steps = workflow.steps.order_by('order')
    transitions = WorkflowTransition.objects.filter(
        from_step__workflow=workflow
    ).select_related('from_step', 'to_step')
    
    # Create transition matrix for visualization
    transition_matrix = {}
    transition_matrix_list = []
    for step in steps:
        matrix_data = {
            'step': step,
            'outgoing': transitions.filter(from_step=step),
            'incoming': transitions.filter(to_step=step)
        }
        transition_matrix[step.id] = matrix_data
        transition_matrix_list.append(matrix_data)
    
    context = {
        'profile': profile,
        'organization': profile.organization,
        'workflow': workflow,
        'steps': steps,
        'transitions': transitions,
        'transition_matrix': transition_matrix,
        'transition_matrix_list': transition_matrix_list,
        'title': f'Manage Transitions - {workflow.name}'
    }
    
    return render(request, 'cflows/workflow_transitions_manager.html', context)


@login_required
@require_business_organization
def create_workflow_transition(request, workflow_id, from_step_id):
    """Create a new workflow transition from a specific step"""
    profile = get_user_profile(request)
    if not profile or not profile.organization:
        return redirect('cflows:index')
    
    workflow = get_object_or_404(
        Workflow, 
        id=workflow_id, 
        organization=profile.organization
    )
    
    from_step = get_object_or_404(
        WorkflowStep,
        id=from_step_id,
        workflow=workflow
    )
    
    # Check permissions
    if not (profile.is_organization_admin or profile.has_staff_panel_access):
        messages.error(request, "You don't have permission to create workflow transitions.")
        return redirect('cflows:workflow_detail', workflow_id=workflow_id)
    
    if request.method == 'POST':
        form = WorkflowTransitionForm(
            request.POST, 
            workflow=workflow, 
            from_step=from_step
        )
        if form.is_valid():
            transition = form.save(commit=False)
            transition.from_step = from_step
            transition.save()
            
            messages.success(request, f"Transition created from '{from_step.name}' to '{transition.to_step.name}'")
            return redirect('cflows:workflow_transitions_manager', workflow_id=workflow_id)
    else:
        form = WorkflowTransitionForm(workflow=workflow, from_step=from_step)
    
    context = {
        'profile': profile,
        'organization': profile.organization,
        'workflow': workflow,
        'from_step': from_step,
        'form': form,
        'title': f'Create Transition from {from_step.name}'
    }
    
    return render(request, 'cflows/create_workflow_transition.html', context)


@login_required
@require_business_organization
def edit_workflow_transition(request, transition_id):
    """Edit an existing workflow transition"""
    profile = get_user_profile(request)
    if not profile or not profile.organization:
        return redirect('cflows:index')
    
    transition = get_object_or_404(WorkflowTransition, id=transition_id)
    workflow = transition.from_step.workflow
    
    # Check organization access
    if workflow.organization != profile.organization:
        messages.error(request, "You don't have access to this workflow.")
        return redirect('cflows:index')
    
    # Check permissions
    if not (profile.is_organization_admin or profile.has_staff_panel_access):
        messages.error(request, "You don't have permission to edit workflow transitions.")
        return redirect('cflows:workflow_detail', workflow_id=workflow.id)
    
    if request.method == 'POST':
        form = WorkflowTransitionForm(
            request.POST, 
            instance=transition,
            workflow=workflow, 
            from_step=transition.from_step
        )
        if form.is_valid():
            form.save()
            messages.success(request, f"Transition updated successfully")
            return redirect('cflows:workflow_transitions_manager', workflow_id=workflow.id)
    else:
        form = WorkflowTransitionForm(
            instance=transition,
            workflow=workflow, 
            from_step=transition.from_step
        )
    
    context = {
        'profile': profile,
        'organization': profile.organization,
        'workflow': workflow,
        'transition': transition,
        'form': form,
        'title': f'Edit Transition: {transition.from_step.name} → {transition.to_step.name}'
    }
    
    return render(request, 'cflows/edit_workflow_transition.html', context)


@login_required
@require_business_organization
@require_http_methods(["POST"])
def delete_workflow_transition(request, transition_id):
    """Delete a workflow transition"""
    profile = get_user_profile(request)
    if not profile or not profile.organization:
        return JsonResponse({'success': False, 'error': 'Authentication required'})
    
    transition = get_object_or_404(WorkflowTransition, id=transition_id)
    workflow = transition.from_step.workflow
    
    # Check organization access
    if workflow.organization != profile.organization:
        return JsonResponse({'success': False, 'error': 'Access denied'})
    
    # Check permissions
    if not (profile.is_organization_admin or profile.has_staff_panel_access):
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    try:
        from_step_name = transition.from_step.name
        to_step_name = transition.to_step.name
        transition.delete()
        
        return JsonResponse({
            'success': True, 
            'message': f"Transition from '{from_step_name}' to '{to_step_name}' deleted successfully"
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_business_organization
def bulk_create_transitions(request, workflow_id):
    """Create multiple transitions at once using patterns"""
    profile = get_user_profile(request)
    if not profile or not profile.organization:
        return redirect('cflows:index')
    
    workflow = get_object_or_404(
        Workflow, 
        id=workflow_id, 
        organization=profile.organization
    )
    
    # Check permissions
    if not (profile.is_organization_admin or profile.has_staff_panel_access):
        messages.error(request, "You don't have permission to create workflow transitions.")
        return redirect('cflows:workflow_detail', workflow_id=workflow_id)
    
    if request.method == 'POST':
        form = BulkTransitionForm(request.POST, workflow=workflow)
        if form.is_valid():
            transitions_created = form.create_transitions()
            
            if transitions_created:
                messages.success(
                    request, 
                    f"Successfully created {len(transitions_created)} transitions using {form.cleaned_data['transition_type']} pattern"
                )
            else:
                messages.info(request, "No new transitions were created (they may already exist)")
            
            return redirect('cflows:workflow_transitions_manager', workflow_id=workflow_id)
    else:
        form = BulkTransitionForm(workflow=workflow)
    
    # Get current transition count for display
    current_transitions = WorkflowTransition.objects.filter(
        from_step__workflow=workflow
    ).count()
    
    context = {
        'profile': profile,
        'organization': profile.organization,
        'workflow': workflow,
        'form': form,
        'current_transitions': current_transitions,
        'steps_count': workflow.steps.count(),
        'title': f'Bulk Create Transitions - {workflow.name}'
    }
    
    return render(request, 'cflows/bulk_create_transitions.html', context)


@login_required
@require_business_organization
def select_workflow_for_transitions(request):
    """Select a workflow to manage transitions for (navbar quick access)"""
    profile = get_user_profile(request)
    if not profile or not profile.organization:
        return redirect('cflows:index')
    
    # Check permissions
    if not (profile.is_organization_admin or profile.has_staff_panel_access):
        messages.error(request, "You don't have permission to manage workflow transitions.")
        return redirect('cflows:index')
    
    if request.method == 'POST':
        workflow_id = request.POST.get('workflow_id')
        if workflow_id:
            return redirect('cflows:workflow_transitions_manager', workflow_id=workflow_id)
        else:
            messages.error(request, 'Please select a workflow.')
    
    # Get active workflows for the organization
    workflows = Workflow.objects.filter(
        organization=profile.organization,
        is_active=True
    ).annotate(
        steps_count=Count('steps'),
        transitions_count=Count('steps__outgoing_transitions', distinct=True)
    ).order_by('name')
    
    if not workflows.exists():
        messages.error(request, 'No active workflows found. Create a workflow first.')
        return redirect('cflows:workflow_list')
    
    # If only one workflow, go directly to transition management
    if workflows.count() == 1:
        return redirect('cflows:workflow_transitions_manager', workflow_id=workflows.first().id)
    
    context = {
        'profile': profile,
        'organization': profile.organization,
        'workflows': workflows,
        'title': 'Select Workflow - Manage Transitions',
        'action': 'manage transitions'
    }
    
    return render(request, 'cflows/select_workflow_for_action.html', context)


@login_required
@require_business_organization
def select_workflow_for_bulk_transitions(request):
    """Select a workflow for bulk transition creation (navbar quick access)"""
    profile = get_user_profile(request)
    if not profile or not profile.organization:
        return redirect('cflows:index')
    
    # Check permissions
    if not (profile.is_organization_admin or profile.has_staff_panel_access):
        messages.error(request, "You don't have permission to create workflow transitions.")
        return redirect('cflows:index')
    
    if request.method == 'POST':
        workflow_id = request.POST.get('workflow_id')
        if workflow_id:
            return redirect('cflows:bulk_create_transitions', workflow_id=workflow_id)
        else:
            messages.error(request, 'Please select a workflow.')
    
    # Get active workflows for the organization with steps
    workflows = Workflow.objects.filter(
        organization=profile.organization,
        is_active=True
    ).annotate(
        steps_count=Count('steps'),
        transitions_count=Count('steps__outgoing_transitions', distinct=True)
    ).filter(
        steps_count__gt=1  # Only show workflows with multiple steps
    ).order_by('name')
    
    if not workflows.exists():
        messages.error(request, 'No workflows with multiple steps found. Create workflows with steps first.')
        return redirect('cflows:workflow_list')
    
    # If only one workflow, go directly to bulk transition creation
    if workflows.count() == 1:
        return redirect('cflows:bulk_create_transitions', workflow_id=workflows.first().id)
    
    context = {
        'profile': profile,
        'organization': profile.organization,
        'workflows': workflows,
        'title': 'Select Workflow - Bulk Create Transitions',
        'action': 'create bulk transitions'
    }
    
    return render(request, 'cflows/select_workflow_for_action.html', context)
