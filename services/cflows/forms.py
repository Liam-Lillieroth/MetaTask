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
            'title', 'description', 'rich_content', 'priority',
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

    def __init__(self, *args, organization=None, workflow=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            # Filter assignees to organization members
            self.fields['current_assignee'].queryset = UserProfile.objects.filter(
                organization=organization, user__is_active=True
            )
        
        # Handle tags display
        if self.instance and self.instance.pk:
            self.fields['tags_input'].initial = ', '.join(self.instance.tags)
        
        # Add custom fields for this organization
        if organization:
            from .models import CustomField
            custom_fields = CustomField.objects.filter(
                organization=organization,
                is_active=True
            )
            
            # Filter by workflow if provided
            if workflow:
                custom_fields = custom_fields.filter(
                    models.Q(workflows__isnull=True) | models.Q(workflows=workflow)
                )
            
            # Sort by section and order
            custom_fields = custom_fields.order_by('section', 'order', 'label')
            
            # Add each custom field to the form
            for custom_field in custom_fields:
                field_name = f'custom_{custom_field.id}'
                self.fields[field_name] = custom_field.get_form_field()
                
                # Set initial value if editing existing work item
                if self.instance and self.instance.pk:
                    try:
                        from .models import WorkItemCustomFieldValue
                        custom_value = WorkItemCustomFieldValue.objects.get(
                            work_item=self.instance,
                            custom_field=custom_field
                        )
                        if custom_field.field_type == 'checkbox':
                            self.fields[field_name].initial = custom_value.value.lower() in ['true', '1', 'yes']
                        elif custom_field.field_type == 'multiselect':
                            import json
                            try:
                                self.fields[field_name].initial = json.loads(custom_value.value)
                            except json.JSONDecodeError:
                                self.fields[field_name].initial = []
                        else:
                            self.fields[field_name].initial = custom_value.value
                    except WorkItemCustomFieldValue.DoesNotExist:
                        pass

    def clean_tags_input(self):
        tags_input = self.cleaned_data.get('tags_input', '')
        if tags_input:
            # Handle both string and list inputs
            if isinstance(tags_input, list):
                return tags_input
            elif isinstance(tags_input, str):
                tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
                return tags
        return []

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Handle tags from tags_input
        tags_data = self.clean_tags_input()
        instance.tags = tags_data
        
        if commit:
            instance.save()
            # Save custom field values
            self.save_custom_fields(instance)
        
        return instance
    
    def save_custom_fields(self, work_item):
        """Save custom field values for the work item"""
        from .models import CustomField, WorkItemCustomFieldValue
        
        for field_name, value in self.cleaned_data.items():
            if field_name.startswith('custom_'):
                try:
                    custom_field_id = int(field_name.replace('custom_', ''))
                    custom_field = CustomField.objects.get(id=custom_field_id)
                    
                    # Get or create the custom field value
                    custom_value, created = WorkItemCustomFieldValue.objects.get_or_create(
                        work_item=work_item,
                        custom_field=custom_field
                    )
                    
                    # Set the value based on field type
                    custom_value.set_value(value)
                    custom_value.save()
                    
                except (ValueError, CustomField.DoesNotExist):
                    continue


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
