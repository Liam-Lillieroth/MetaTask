from django.db import models
from django.conf import settings
import uuid


class BaseModel(models.Model):
    """
    Base model with common fields for all Mediap models
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_created'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_updated'
    )
    
    class Meta:
        abstract = True


class AuditLog(models.Model):
    """
    Audit log for tracking user actions across the platform
    """
    ACTION_TYPES = [
        ('create', 'Create'),
        ('read', 'Read'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('permission_granted', 'Permission Granted'),
        ('permission_revoked', 'Permission Revoked'),
        ('export', 'Data Export'),
        ('import', 'Data Import'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_TYPES)
    content_type = models.CharField(max_length=100, help_text="Model name")
    object_id = models.CharField(max_length=100, blank=True)
    object_repr = models.CharField(max_length=200, blank=True)
    
    # Request information
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Additional context
    changes = models.JSONField(default=dict, help_text="Changed fields and values")
    additional_data = models.JSONField(default=dict, help_text="Additional context data")
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['timestamp']),
        ]
        ordering = ['-timestamp']
    
    def __str__(self):
        user_str = self.user.username if self.user else 'Anonymous'
        return f"{user_str} {self.action} {self.content_type} at {self.timestamp}"


class SystemConfiguration(models.Model):
    """
    System-wide configuration settings
    """
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    value_type = models.CharField(
        max_length=20,
        choices=[
            ('string', 'String'),
            ('integer', 'Integer'),
            ('boolean', 'Boolean'),
            ('json', 'JSON'),
            ('float', 'Float'),
        ],
        default='string'
    )
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, default='general')
    is_sensitive = models.BooleanField(default=False, help_text="Whether this setting contains sensitive data")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['category', 'key']
        indexes = [
            models.Index(fields=['category']),
        ]
    
    def __str__(self):
        return f"{self.key} = {self.value[:50]}..."
    
    def get_typed_value(self):
        """Return the value converted to its proper type"""
        if self.value_type == 'integer':
            return int(self.value)
        elif self.value_type == 'boolean':
            return self.value.lower() in ('true', '1', 'yes')
        elif self.value_type == 'float':
            return float(self.value)
        elif self.value_type == 'json':
            import json
            return json.loads(self.value)
        else:
            return self.value


class Notification(models.Model):
    """
    In-app notification system
    """
    NOTIFICATION_TYPES = [
        ('info', 'Information'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('system', 'System'),
    ]
    
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='info')
    
    # Link to related object
    content_type = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=100, blank=True)
    action_url = models.URLField(blank=True, help_text="URL for action button")
    action_text = models.CharField(max_length=50, blank=True)
    
    # Status tracking
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Email/push notification status
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Auto-delete after this date")
    
    class Meta:
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['created_at']),
            models.Index(fields=['expires_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} for {self.recipient.username}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class FileUpload(models.Model):
    """
    Generic file upload model for the platform
    """
    file = models.FileField(upload_to='uploads/%Y/%m/')
    original_filename = models.CharField(max_length=255)
    file_size = models.BigIntegerField()
    mime_type = models.CharField(max_length=100)
    
    # File metadata
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    upload_session = models.UUIDField(default=uuid.uuid4, help_text="Group related files")
    
    # Content association
    content_type = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=100, blank=True)
    
    # File processing status
    is_processed = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True)
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['uploaded_by', 'uploaded_at']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['upload_session']),
        ]
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.original_filename} by {self.uploaded_by.username}"
    
    @property
    def file_size_human(self):
        """Return human readable file size"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.file_size < 1024.0:
                return f"{self.file_size:.1f} {unit}"
            self.file_size /= 1024.0
        return f"{self.file_size:.1f} TB"
