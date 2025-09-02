from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django.utils.text import slugify


class CustomUser(AbstractUser):
    """
    Extended user model for Mediap platform
    """
    REFERRAL_SOURCES = [
        ('search', 'Search Engine'),
        ('social_media', 'Social Media'),
        ('referral', 'Referral'),
        ('advertisement', 'Advertisement'),
        ('direct', 'Direct Visit'),
        ('other', 'Other'),
    ]
    
    TEAM_SIZES = [
        ('1', 'Just Me'),
        ('2-10', '2-10 people'),
        ('11-50', '11-50 people'),
        ('51-200', '51-200 people'),
        ('201-500', '201-500 people'),
        ('500+', '500+ people'),
    ]
    
    # Extended fields
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150) 
    phone_number = models.CharField(
        max_length=17,
        blank=True,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$', 
                                 message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")]
    )
    
    # Registration info
    referral_source = models.CharField(max_length=20, choices=REFERRAL_SOURCES, blank=True)
    team_size = models.CharField(max_length=10, choices=TEAM_SIZES, blank=True)
    job_title = models.CharField(max_length=255, blank=True)
    organization_name = models.CharField(max_length=255, blank=True)
    
    # GDPR compliance fields
    privacy_policy_accepted = models.BooleanField(default=False)
    privacy_policy_accepted_date = models.DateTimeField(null=True, blank=True)
    terms_accepted = models.BooleanField(default=False)
    terms_accepted_date = models.DateTimeField(null=True, blank=True)
    marketing_consent = models.BooleanField(default=False)
    
    # Settings
    timezone = models.CharField(max_length=50, default='UTC')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.username} ({self.email})"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class Organization(models.Model):
    """
    Represents a company or team account
    """
    COMPANY_TYPES = [
        ('startup', 'Startup'),
        ('smb', 'Small-Medium Business'),
        ('enterprise', 'Enterprise'),
        ('non_profit', 'Non-Profit'),
        ('education', 'Education'),
        ('other', 'Other'),
    ]

    PURPOSES = [
        ('project_management', 'Project Management'),
        ('marketing', 'Marketing'),
        ('sales', 'Sales'),
        ('development', 'Development'),
        ('hr', 'Human Resources'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    owner = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='owned_organization')
    team_size = models.CharField(max_length=20, choices=CustomUser.TEAM_SIZES, blank=True, null=True)
    company_type = models.CharField(max_length=50, choices=COMPANY_TYPES, blank=True, null=True)
    purpose = models.CharField(max_length=50, choices=PURPOSES, blank=True, null=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    
    # Contact information
    contact_email = models.EmailField(blank=True)
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

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class OrganizationMember(models.Model):
    """
    Manages users within an organization, including their roles and invitation status
    """
    ROLES = [
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('member', 'Member'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='organization_memberships')
    role = models.CharField(max_length=20, choices=ROLES, default='member')
    is_active = models.BooleanField(default=True)
    invited_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='invited_members')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('organization', 'user')

    def __str__(self):
        return f'{self.user.username} in {self.organization.name} ({self.role})'


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
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='roles')
    role = models.CharField(max_length=50, choices=ROLE_CHOICES)
    service = models.CharField(max_length=100, blank=True, help_text="Service this role applies to (e.g., 'cflows', 'job_planning')")
    granted_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='granted_roles')
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
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
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
