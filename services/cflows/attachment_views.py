"""
CFlows Work Item Attachment and Comment Views
Handles file uploads and comments for work items
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.http import require_POST
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone
from django.db import transaction
import os
import mimetypes
from core.models import UserProfile
from core.views import require_organization_access
from .models import WorkItem, WorkItemComment, WorkItemAttachment, WorkItemRevision
from .forms import WorkItemCommentForm, WorkItemAttachmentForm


def get_user_profile(request):
    """Get user profile for the current user"""
    if not request.user.is_authenticated:
        return None
    
    try:
        return request.user.mediap_profile
    except UserProfile.DoesNotExist:
        return None


@login_required
@require_organization_access
@require_POST
def add_comment(request, work_item_id):
    """Add a comment to a work item"""
    profile = get_user_profile(request)
    if not profile:
        return JsonResponse({'success': False, 'error': 'No user profile found'})
    
    work_item = get_object_or_404(
        WorkItem,
        id=work_item_id,
        workflow__organization=profile.organization
    )
    
    form = WorkItemCommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.work_item = work_item
        comment.author = profile
        
        # Handle reply to parent comment
        parent_id = request.POST.get('parent_id')
        if parent_id:
            try:
                parent_comment = WorkItemComment.objects.get(
                    id=parent_id,
                    work_item=work_item
                )
                comment.parent = parent_comment
            except WorkItemComment.DoesNotExist:
                pass
        
        comment.save()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'comment': {
                    'id': comment.id,
                    'content': comment.content,
                    'author_name': comment.author.user.get_full_name() or comment.author.user.username,
                    'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M'),
                    'is_system_comment': comment.is_system_comment,
                }
            })
        else:
            messages.success(request, 'Comment added successfully!')
            return redirect('cflows:work_item_detail', work_item_id=work_item.id)
    else:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors})
        else:
            messages.error(request, 'Error adding comment. Please check your input.')
            return redirect('cflows:work_item_detail', work_item_id=work_item.id)


@login_required
@require_organization_access
@require_POST
def upload_attachment(request, work_item_id):
    """Upload an attachment to a work item"""
    profile = get_user_profile(request)
    if not profile:
        return JsonResponse({'success': False, 'error': 'No user profile found'})
    
    work_item = get_object_or_404(
        WorkItem,
        id=work_item_id,
        workflow__organization=profile.organization
    )
    
    if 'file' not in request.FILES:
        messages.error(request, 'No file selected')
        return redirect('cflows:work_item_detail', work_item_id=work_item.id)
    
    uploaded_file = request.FILES['file']
    
    # Validate file size (limit to 10MB)
    if uploaded_file.size > 10 * 1024 * 1024:
        messages.error(request, 'File size must be less than 10MB')
        return redirect('cflows:work_item_detail', work_item_id=work_item.id)
    
    # Validate file type (basic security check)
    allowed_types = [
        'application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'text/plain', 'text/csv',
        'image/jpeg', 'image/png', 'image/gif', 'image/webp',
        'application/zip', 'application/x-rar-compressed',
    ]
    
    content_type = uploaded_file.content_type
    if content_type not in allowed_types:
        messages.error(request, 'File type not allowed')
        return redirect('cflows:work_item_detail', work_item_id=work_item.id)
    
    try:
        # Create attachment record
        attachment = WorkItemAttachment(
            work_item=work_item,
            uploaded_by=profile,
            filename=uploaded_file.name,
            file_size=uploaded_file.size,
            content_type=content_type,
            description=request.POST.get('description', '')
        )
        
        # Save file to storage
        attachment.file = uploaded_file
        attachment.save()
        
        # Add system comment
        WorkItemComment.objects.create(
            work_item=work_item,
            content=f"File attached: {attachment.filename}",
            author=profile,
            is_system_comment=True
        )
        
        messages.success(request, f'File "{uploaded_file.name}" uploaded successfully!')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'attachment': {
                    'id': attachment.id,
                    'filename': attachment.filename,
                    'file_size': attachment.file_size,
                    'content_type': attachment.content_type,
                    'uploaded_at': attachment.uploaded_at.strftime('%Y-%m-%d %H:%M'),
                    'uploaded_by': profile.user.get_full_name() or profile.user.username,
                    'url': attachment.file.url if attachment.file else None,
                }
            })
        else:
            return redirect('cflows:work_item_detail', work_item_id=work_item.id)
            
    except Exception as e:
        messages.error(request, f'Error uploading file: {str(e)}')
        return redirect('cflows:work_item_detail', work_item_id=work_item.id)


@login_required
@require_organization_access
def download_attachment(request, work_item_id, attachment_id):
    """Download a work item attachment"""
    profile = get_user_profile(request)
    if not profile:
        raise Http404
    
    work_item = get_object_or_404(
        WorkItem,
        id=work_item_id,
        workflow__organization=profile.organization
    )
    
    attachment = get_object_or_404(
        WorkItemAttachment,
        id=attachment_id,
        work_item=work_item
    )
    
    try:
        if attachment.file and default_storage.exists(attachment.file.name):
            response = HttpResponse(
                default_storage.open(attachment.file.name).read(),
                content_type=attachment.content_type or 'application/octet-stream'
            )
            response['Content-Disposition'] = f'attachment; filename="{attachment.filename}"'
            return response
        else:
            raise Http404
    except Exception:
        raise Http404


@login_required
@require_organization_access
@require_POST
def delete_attachment(request, work_item_id, attachment_id):
    """Delete a work item attachment"""
    profile = get_user_profile(request)
    if not profile:
        return JsonResponse({'success': False, 'error': 'No user profile found'})
    
    work_item = get_object_or_404(
        WorkItem,
        id=work_item_id,
        workflow__organization=profile.organization
    )
    
    attachment = get_object_or_404(
        WorkItemAttachment,
        id=attachment_id,
        work_item=work_item
    )
    
    # Only allow deletion by uploader or organization admin
    if attachment.uploaded_by != profile and not profile.is_organization_admin:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    try:
        filename = attachment.filename
        
        # Delete the file from storage
        if attachment.file and default_storage.exists(attachment.file.name):
            default_storage.delete(attachment.file.name)
        
        # Delete the database record
        attachment.delete()
        
        # Add system comment
        WorkItemComment.objects.create(
            work_item=work_item,
            content=f"File deleted: {filename}",
            author=profile,
            is_system_comment=True
        )
        
        messages.success(request, f'File "{filename}" deleted successfully!')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': f'File "{filename}" deleted'})
        else:
            return redirect('cflows:work_item_detail', work_item_id=work_item.id)
            
    except Exception as e:
        error_msg = f'Error deleting file: {str(e)}'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': error_msg})
        else:
            messages.error(request, error_msg)
            return redirect('cflows:work_item_detail', work_item_id=work_item.id)


@login_required
@require_organization_access
@require_POST
def edit_comment(request, work_item_id, comment_id):
    """Edit a comment"""
    profile = get_user_profile(request)
    if not profile:
        return JsonResponse({'success': False, 'error': 'No user profile found'})
    
    work_item = get_object_or_404(
        WorkItem,
        id=work_item_id,
        workflow__organization=profile.organization
    )
    
    comment = get_object_or_404(
        WorkItemComment,
        id=comment_id,
        work_item=work_item
    )
    
    # Only allow editing by comment author or organization admin
    if comment.author != profile and not profile.is_organization_admin:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    # Don't allow editing system comments
    if comment.is_system_comment:
        return JsonResponse({'success': False, 'error': 'Cannot edit system comments'})
    
    new_content = request.POST.get('content', '').strip()
    if not new_content:
        return JsonResponse({'success': False, 'error': 'Comment content cannot be empty'})
    
    comment.content = new_content
    comment.is_edited = True
    comment.save()
    
    messages.success(request, 'Comment updated successfully!')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'comment': {
                'id': comment.id,
                'content': comment.content,
                'is_edited': comment.is_edited,
                'updated_at': comment.updated_at.strftime('%Y-%m-%d %H:%M'),
            }
        })
    else:
        return redirect('cflows:work_item_detail', work_item_id=work_item.id)


@login_required
@require_organization_access
@require_POST
def delete_comment(request, work_item_id, comment_id):
    """Delete a comment"""
    profile = get_user_profile(request)
    if not profile:
        return JsonResponse({'success': False, 'error': 'No user profile found'})
    
    work_item = get_object_or_404(
        WorkItem,
        id=work_item_id,
        workflow__organization=profile.organization
    )
    
    comment = get_object_or_404(
        WorkItemComment,
        id=comment_id,
        work_item=work_item
    )
    
    # Only allow deletion by comment author or organization admin
    if comment.author != profile and not profile.is_organization_admin:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    # Don't allow deleting system comments
    if comment.is_system_comment:
        return JsonResponse({'success': False, 'error': 'Cannot delete system comments'})
    
    comment.delete()
    
    messages.success(request, 'Comment deleted successfully!')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'Comment deleted'})
    else:
        return redirect('cflows:work_item_detail', work_item_id=work_item.id)
