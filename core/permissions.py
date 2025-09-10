"""
Role-Based Access Control (RBAC) system for MediaP
Provides flexible permission management at the organization level
"""

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone


class Permission(models.Model):
    """System-wide permissions that can be assigned to roles"""
    PERMISSION_CATEGORIES = [
        ('workflow', 'Workflow Management'),
        ('workitem', 'Work Item Management'),
        ('team', 'Team Management'),
        ('user', 'User Management'),
        ('booking', 'Booking Management'),
        ('reporting', 'Reporting & Analytics'),
        ('system', 'System Administration'),
        ('custom', 'Custom Permissions')
    ]
    
    codename = models.CharField(
        max_length=100, 
        unique=True, 
        help_text="Unique permission identifier (e.g., 'workflow.create')"
    )
    name = models.CharField(
        max_length=255, 
        help_text="Human-readable permission name"
    )
    description = models.TextField(
        help_text="What this permission allows users to do"
    )
    category = models.CharField(
        max_length=20, 
        choices=PERMISSION_CATEGORIES, 
        default='custom'
    )
    
    # Service-specific permissions
    service = models.CharField(
        max_length=50, 
        default='core', 
        help_text="Which service this permission belongs to"
    )
    
    # Permission scope
    is_global = models.BooleanField(
        default=False, 
        help_text="Can this permission affect the entire organization?"
    )
    requires_resource = models.BooleanField(
        default=False, 
        help_text="Does this permission require a specific resource?"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['category', 'name']
        indexes = [
            models.Index(fields=['category', 'service']),
            models.Index(fields=['codename']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.codename})"


class Role(models.Model):
    """Organization-specific roles with assigned permissions"""
    ROLE_TYPES = [
        ('system', 'System Role'),
        ('custom', 'Custom Role')
    ]
    
    organization = models.ForeignKey(
        'core.Organization', 
        on_delete=models.CASCADE, 
        related_name='roles'
    )
    name = models.CharField(
        max_length=100, 
        help_text="Role name (e.g., 'Project Manager', 'Team Lead')"
    )
    description = models.TextField(
        blank=True, 
        help_text="Description of what this role does"
    )
    
    # Role metadata
    role_type = models.CharField(
        max_length=20, 
        choices=ROLE_TYPES, 
        default='custom'
    )
    color = models.CharField(
        max_length=7, 
        default='#6B7280', 
        help_text="Hex color for visual identification"
    )
    
    # Permissions
    permissions = models.ManyToManyField(
        Permission, 
        through='RolePermission', 
        related_name='roles'
    )
    
    # Hierarchy and inheritance
    inherits_from = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='child_roles', 
        help_text="Inherit permissions from another role"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(
        default=False, 
        help_text="Assign this role to new organization members"
    )
    
    # Restrictions
    max_users = models.PositiveIntegerField(
        null=True, 
        blank=True, 
        help_text="Maximum users that can have this role"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'core.UserProfile', 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_roles'
    )
    
    class Meta:
        unique_together = ['organization', 'name']
        ordering = ['organization', 'name']
        indexes = [
            models.Index(fields=['organization', 'is_active']),
            models.Index(fields=['organization', 'is_default']),
        ]
    
    def __str__(self):
        return f"{self.organization.name} - {self.name}"
    
    def get_all_permissions(self):
        """Get all permissions including inherited ones"""
        permissions = set(self.permissions.all())
        
        # Add inherited permissions
        if self.inherits_from:
            permissions.update(self.inherits_from.get_all_permissions())
        
        return permissions
    
    def get_inherited_permissions(self):
        """Get permissions inherited from parent roles"""
        if not self.inherits_from:
            return Permission.objects.none()
        
        # Return queryset instead of set for consistency
        inherited_perms = list(self.inherits_from.get_all_permissions())
        if inherited_perms:
            return Permission.objects.filter(id__in=[p.id for p in inherited_perms])
        return Permission.objects.none()
    
    def get_user_count(self):
        """Get number of users with this role"""
        return self.user_assignments.filter(is_active=True).count()


class RolePermission(models.Model):
    """Through model for role-permission relationships with additional context"""
    role = models.ForeignKey(
        Role, 
        on_delete=models.CASCADE, 
        related_name='permission_assignments'
    )
    permission = models.ForeignKey(
        Permission, 
        on_delete=models.CASCADE, 
        related_name='role_assignments'
    )
    
    # Permission constraints
    resource_type = models.ForeignKey(
        ContentType, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        help_text="Limit permission to specific resource type"
    )
    resource_id = models.PositiveIntegerField(
        null=True, 
        blank=True,
        help_text="Limit permission to specific resource instance"
    )
    resource_object = GenericForeignKey('resource_type', 'resource_id')
    
    # Conditions
    conditions = models.JSONField(
        default=dict, 
        blank=True, 
        help_text="Additional conditions for permission (time, location, etc.)"
    )
    
    granted_at = models.DateTimeField(auto_now_add=True)
    granted_by = models.ForeignKey(
        'core.UserProfile', 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='granted_permissions'
    )
    
    class Meta:
        unique_together = ['role', 'permission', 'resource_type', 'resource_id']
        indexes = [
            models.Index(fields=['role', 'permission']),
            models.Index(fields=['resource_type', 'resource_id']),
        ]


class UserRoleAssignment(models.Model):
    """Assign roles to users with context and time limits"""
    user_profile = models.ForeignKey(
        'core.UserProfile', 
        on_delete=models.CASCADE, 
        related_name='role_assignments'
    )
    role = models.ForeignKey(
        Role, 
        on_delete=models.CASCADE, 
        related_name='user_assignments'
    )
    
    # Assignment context
    resource_type = models.ForeignKey(
        ContentType, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        help_text="Scope role to specific resource type (e.g., specific team)"
    )
    resource_id = models.PositiveIntegerField(null=True, blank=True)
    resource_object = GenericForeignKey('resource_type', 'resource_id')
    
    # Time constraints
    valid_from = models.DateTimeField(
        null=True, 
        blank=True, 
        help_text="When this role assignment becomes active"
    )
    valid_until = models.DateTimeField(
        null=True, 
        blank=True, 
        help_text="When this role assignment expires"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Metadata
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        'core.UserProfile', 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='assigned_roles'
    )
    notes = models.TextField(
        blank=True, 
        help_text="Reason for assignment or additional context"
    )
    
    class Meta:
        unique_together = ['user_profile', 'role', 'resource_type', 'resource_id']
        indexes = [
            models.Index(fields=['user_profile', 'is_active']),
            models.Index(fields=['role', 'is_active']),
            models.Index(fields=['resource_type', 'resource_id']),
        ]
    
    def is_currently_valid(self):
        """Check if role assignment is currently valid"""
        now = timezone.now()
        
        if not self.is_active:
            return False
        
        if self.valid_from and now < self.valid_from:
            return False
            
        if self.valid_until and now > self.valid_until:
            return False
            
        return True
    
    def __str__(self):
        return f"{self.user_profile.user.get_full_name()} - {self.role.name}"
