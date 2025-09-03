from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.db import models
from core.models import Organization, UserProfile, Team, JobType
from .models import (
    Workflow, WorkflowStep, WorkflowTransition, WorkflowTemplate,
    WorkItem, WorkItemComment, WorkItemAttachment, TeamBooking
)
import json


class WorkflowForm(forms.ModelForm):
    """Form for creating and editing workflows"""
    
    class Meta:
        model = Workflow
        fields = [
            'name', 'description', 'template', 'is_shared', 
            'auto_assign', 'requires_approval'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500',
                'placeholder': 'Enter workflow name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500',
                'placeholder': 'Describe this workflow...',
                'rows': 3
            }),
            'template': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500'
            }),
            'is_shared': forms.CheckboxInput(attrs={
                'class': 'rounded text-purple-600 focus:ring-purple-500'
            }),
            'auto_assign': forms.CheckboxInput(attrs={
                'class': 'rounded text-purple-600 focus:ring-purple-500'
            }),
            'requires_approval': forms.CheckboxInput(attrs={
                'class': 'rounded text-purple-600 focus:ring-purple-500'
            }),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization = organization
        
        if organization:
            # Filter templates available to this organization
            self.fields['template'].queryset = WorkflowTemplate.objects.filter(
                models.Q(is_public=True) | models.Q(created_by_org=organization)
            )


class WorkflowStepForm(forms.ModelForm):
    """Form for creating and editing workflow steps"""
    
    class Meta:
        model = WorkflowStep
        fields = [
            'name', 'description', 'order', 'assigned_team',
            'requires_booking', 'estimated_duration_hours', 'is_terminal'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500',
                'placeholder': 'Step name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500',
                'placeholder': 'Step description...',
                'rows': 2
            }),
            'order': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500',
                'min': '1'
            }),
            'assigned_team': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500'
            }),
            'estimated_duration_hours': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500',
                'step': '0.25',
                'min': '0'
            }),
            'requires_booking': forms.CheckboxInput(attrs={
                'class': 'rounded text-purple-600 focus:ring-purple-500'
            }),
            'is_terminal': forms.CheckboxInput(attrs={
                'class': 'rounded text-purple-600 focus:ring-purple-500'
            }),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields['assigned_team'].queryset = Team.objects.filter(
                organization=organization, is_active=True
            )


class WorkItemForm(forms.ModelForm):
    """Form for creating and editing work items"""
    
    class Meta:
        model = WorkItem
        fields = [
            'title', 'description', 'rich_content', 'priority', 'tags',
            'current_assignee', 'due_date', 'estimated_duration'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500',
                'placeholder': 'Work item title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500',
                'placeholder': 'Brief description...',
                'rows': 3
            }),
            'rich_content': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500',
                'placeholder': 'Detailed content (supports HTML)...',
                'rows': 6,
                'id': 'rich-content-editor'
            }),
            'priority': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500'
            }),
            'current_assignee': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500'
            }),
            'due_date': forms.DateTimeInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500',
                'type': 'datetime-local'
            }),
            'estimated_duration': forms.TimeInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500',
                'placeholder': 'HH:MM:SS'
            }),
        }

    tags_input = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500',
            'placeholder': 'Enter tags separated by commas',
            'data-tags-input': 'true'
        }),
        help_text='Enter tags separated by commas'
    )

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            # Filter assignees to organization members
            self.fields['current_assignee'].queryset = UserProfile.objects.filter(
                organization=organization, user__is_active=True
            )
        
        # Handle tags display
        if self.instance and self.instance.pk:
            self.fields['tags_input'].initial = ', '.join(self.instance.tags)

    def clean_tags_input(self):
        tags_input = self.cleaned_data.get('tags_input', '')
        if tags_input:
            tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
            return tags
        return []

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.tags = self.clean_tags_input()
        if commit:
            instance.save()
        return instance


class WorkItemCommentForm(forms.ModelForm):
    """Form for adding comments to work items"""
    
    class Meta:
        model = WorkItemComment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500',
                'placeholder': 'Add a comment...',
                'rows': 3
            })
        }


class WorkItemAttachmentForm(forms.ModelForm):
    """Form for uploading attachments to work items"""
    
    class Meta:
        model = WorkItemAttachment
        fields = ['file', 'description']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500',
                'accept': '.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.jpg,.jpeg,.png,.gif,.zip,.rar'
            }),
            'description': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500',
                'placeholder': 'Optional description...'
            })
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.file:
            instance.filename = instance.file.name
            instance.file_size = instance.file.size
            instance.content_type = instance.file.content_type or 'application/octet-stream'
        if commit:
            instance.save()
        return instance


class WorkflowTransitionForm(forms.ModelForm):
    """Form for creating transitions between workflow steps"""
    
    class Meta:
        model = WorkflowTransition
        fields = ['to_step', 'label']
        widgets = {
            'to_step': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500'
            }),
            'label': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500',
                'placeholder': 'Transition label (e.g., "Approve", "Reject")'
            })
        }

    def __init__(self, *args, workflow=None, from_step=None, **kwargs):
        super().__init__(*args, **kwargs)
        if workflow:
            # Only show steps from the same workflow, excluding the from_step
            steps = WorkflowStep.objects.filter(workflow=workflow)
            if from_step:
                steps = steps.exclude(id=from_step.id)
            self.fields['to_step'].queryset = steps


class TeamBookingForm(forms.ModelForm):
    """Form for creating team bookings"""
    
    class Meta:
        model = TeamBooking
        fields = [
            'title', 'description', 'job_type', 'start_time', 'end_time',
            'required_members'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500',
                'placeholder': 'Booking title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500',
                'placeholder': 'Booking description...',
                'rows': 3
            }),
            'job_type': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500'
            }),
            'start_time': forms.DateTimeInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500',
                'type': 'datetime-local'
            }),
            'end_time': forms.DateTimeInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500',
                'type': 'datetime-local'
            }),
            'required_members': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500',
                'min': '1'
            }),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields['job_type'].queryset = JobType.objects.filter(
                organization=organization, is_active=True
            )

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if start_time and end_time:
            if end_time <= start_time:
                raise ValidationError("End time must be after start time.")

        return cleaned_data
