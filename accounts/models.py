from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator


class User(AbstractUser):
    """
    Extended User model with additional fields for Mediap platform
    """
    email = models.EmailField(unique=True)
    phone_number = models.CharField(
        max_length=17,
        blank=True,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$', 
                                 message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")]
    )
    
    # GDPR compliance fields
    privacy_policy_accepted = models.BooleanField(default=False)
    privacy_policy_accepted_date = models.DateTimeField(null=True, blank=True)
    terms_accepted = models.BooleanField(default=False)
    terms_accepted_date = models.DateTimeField(null=True, blank=True)
    marketing_consent = models.BooleanField(default=False)
    
    # Profile fields
    organization = models.CharField(max_length=255, blank=True)
    job_title = models.CharField(max_length=255, blank=True)
    timezone = models.CharField(max_length=50, default='UTC')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.username} ({self.email})"


class UserRole(models.Model):
    """
    User role model for Mediap platform role management
    """
    ROLE_CHOICES = [
        ('mediap_support', 'Mediap Support'),
        ('mediap_admin', 'Mediap Admin'),
        ('mediap_moderator', 'Mediap Moderator'),
        ('mediap_editor', 'Mediap Editor'),
        ('workflow_manager', 'Workflow Manager'),
        ('process_designer', 'Process Designer'),
        ('job_planner', 'Job Planner'),
        ('resource_manager', 'Resource Manager'),
        ('team_leader', 'Team Leader'),
        ('standard_user', 'Standard User'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='roles')
    role = models.CharField(max_length=50, choices=ROLE_CHOICES)
    service = models.CharField(max_length=100, blank=True, help_text="Service this role applies to (e.g., 'cflows', 'job_planning')")
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='granted_roles')
    granted_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['user', 'role', 'service']
        indexes = [
            models.Index(fields=['user', 'role']),
            models.Index(fields=['service']),
        ]
    
    def __str__(self):
        service_str = f" ({self.service})" if self.service else ""
        return f"{self.user.username} - {self.get_role_display()}{service_str}"


class UserProfile(models.Model):
    """
    Extended user profile for additional Mediap-specific data
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True)
    website = models.URLField(blank=True)
    
    # Notification preferences
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)
    digest_frequency = models.CharField(
        max_length=20,
        choices=[
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('never', 'Never'),
        ],
        default='weekly'
    )
    
    # Analytics and activity tracking (GDPR compliant)
    analytics_consent = models.BooleanField(default=False)
    last_activity = models.DateTimeField(auto_now=True)
    login_count = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"


class Organization(models.Model):
    """
    Organization model for multi-tenant support
    """
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    
    # Contact information
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=17, blank=True)
    
    # Address information
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)
    
    # Organization settings
    is_active = models.BooleanField(default=True)
    max_users = models.PositiveIntegerField(default=100)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class OrganizationMembership(models.Model):
    """
    Membership model to link users to organizations
    """
    MEMBERSHIP_ROLES = [
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('member', 'Member'),
        ('guest', 'Guest'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memberships')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=20, choices=MEMBERSHIP_ROLES, default='member')
    is_active = models.BooleanField(default=True)
    
    joined_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'organization']
        indexes = [
            models.Index(fields=['organization', 'role']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.organization.name} ({self.get_role_display()})"
