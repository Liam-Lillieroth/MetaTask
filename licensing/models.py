from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.utils import timezone


class Service(models.Model):
    """
    Model representing a Mediap service (e.g., CFlows, Job Planning)
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    version = models.CharField(max_length=20, default='1.0.0')
    is_active = models.BooleanField(default=True)
    
    # Service metadata
    icon = models.CharField(max_length=100, blank=True, help_text="CSS class or icon identifier")
    color = models.CharField(max_length=7, default='#000000', help_text="Hex color code")
    sort_order = models.PositiveIntegerField(default=0)
    
    # Personal use settings
    allows_personal_free = models.BooleanField(default=True, help_text="Allow free personal use")
    personal_free_limits = models.JSONField(default=dict, help_text="Limits for personal free accounts")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return self.name


class LicenseType(models.Model):
    """
    Different types of licenses available for services
    """
    LICENSE_TYPES = [
        ('personal_free', 'Personal Free'),
        ('basic', 'Basic'),
        ('professional', 'Professional'),
        ('enterprise', 'Enterprise'),
        ('custom', 'Custom'),
    ]
    
    name = models.CharField(max_length=50, choices=LICENSE_TYPES)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='license_types')
    display_name = models.CharField(max_length=100, help_text="User-friendly name")
    
    # Pricing
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Limitations
    max_users = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum users allowed, null for unlimited")
    max_projects = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum projects allowed, null for unlimited") 
    max_workflows = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum workflows allowed, null for unlimited")
    max_storage_gb = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum storage in GB, null for unlimited")
    max_api_calls_per_day = models.PositiveIntegerField(null=True, blank=True, help_text="API rate limits")
    
    # Features
    features = models.JSONField(default=list, help_text="List of included features")
    restrictions = models.JSONField(default=list, help_text="List of restrictions")
    
    # Personal account settings
    is_personal_only = models.BooleanField(default=False, help_text="Available only for personal accounts")
    requires_organization = models.BooleanField(default=False, help_text="Requires organization membership")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['service', 'name']
        ordering = ['service', 'price_monthly']
    
    def __str__(self):
        return f"{self.service.name} - {self.display_name}"
    
    def get_limits_dict(self):
        """Return limits as a dictionary"""
        return {
            'users': self.max_users,
            'projects': self.max_projects,
            'workflows': self.max_workflows,
            'storage_gb': self.max_storage_gb,
            'api_calls_per_day': self.max_api_calls_per_day,
        }


class License(models.Model):
    """
    License instances for organizations or users
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('suspended', 'Suspended'),
        ('cancelled', 'Cancelled'),
        ('pending', 'Pending'),
        ('trial', 'Trial'),
    ]
    
    BILLING_CYCLE_CHOICES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
        ('lifetime', 'Lifetime'),
    ]
    
    ACCOUNT_TYPE_CHOICES = [
        ('personal', 'Personal Account'),
        ('organization', 'Organization Account'),
    ]
    
    license_type = models.ForeignKey(LicenseType, on_delete=models.CASCADE)
    organization = models.ForeignKey('core.Organization', on_delete=models.CASCADE, related_name='licenses')
    
    # Account classification
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES, default='organization')
    is_personal_free = models.BooleanField(default=False, help_text="Is this a personal free account")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLE_CHOICES, default='monthly')
    
    # License period
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    trial_end_date = models.DateTimeField(null=True, blank=True)
    
    # Current usage tracking
    current_users = models.PositiveIntegerField(default=0)
    current_projects = models.PositiveIntegerField(default=0)
    current_workflows = models.PositiveIntegerField(default=0)
    current_storage_gb = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    current_api_calls_today = models.PositiveIntegerField(default=0)
    api_calls_reset_date = models.DateField(default=timezone.now)
    
    # Billing information
    last_billing_date = models.DateTimeField(null=True, blank=True)
    next_billing_date = models.DateTimeField(null=True, blank=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Metadata
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['end_date']),
            models.Index(fields=['account_type', 'is_personal_free']),
        ]
        unique_together = ['organization', 'license_type']
    
    def __str__(self):
        return f"{self.organization.name} - {self.license_type}"
    
    def is_valid(self):
        """Check if the license is currently valid"""
        now = timezone.now()
        if self.status not in ['active', 'trial']:
            return False
        if self.end_date and self.end_date < now:
            return False
        if self.status == 'trial' and self.trial_end_date and self.trial_end_date < now:
            return False
        return True
    
    def usage_percentage(self, resource_type):
        """Calculate usage percentage for a given resource type"""
        limits = self.license_type.get_limits_dict()
        max_val = limits.get(resource_type)
        
        if resource_type == 'users':
            current_val = self.current_users
        elif resource_type == 'projects':
            current_val = self.current_projects
        elif resource_type == 'workflows':
            current_val = self.current_workflows
        elif resource_type == 'storage_gb':
            current_val = float(self.current_storage_gb)
        elif resource_type == 'api_calls_per_day':
            current_val = self.current_api_calls_today
        else:
            return 0
        
        if max_val is None:  # Unlimited
            return 0
        if max_val == 0:
            return 100
        
        return min(100, (current_val / max_val) * 100)
    
    def is_at_limit(self, resource_type):
        """Check if at or over the limit for a resource type"""
        return self.usage_percentage(resource_type) >= 100
    
    def can_add_user(self):
        """Check if can add another user"""
        return not self.is_at_limit('users') or self.license_type.max_users is None
    
    def can_add_project(self):
        """Check if can add another project"""
        return not self.is_at_limit('projects') or self.license_type.max_projects is None
    
    def can_add_workflow(self):
        """Check if can add another workflow"""
        return not self.is_at_limit('workflows') or self.license_type.max_workflows is None
    
    def reset_daily_api_calls(self):
        """Reset daily API call counter"""
        today = timezone.now().date()
        if self.api_calls_reset_date < today:
            self.current_api_calls_today = 0
            self.api_calls_reset_date = today
            self.save(update_fields=['current_api_calls_today', 'api_calls_reset_date'])
    
    @classmethod
    def get_or_create_personal_free(cls, user, service_slug):
        """Get or create a personal free license for a user"""
        from core.models import Organization, UserProfile
        
        # Check if user already has an organization
        user_profiles = UserProfile.objects.filter(user=user, is_active=True)
        if user_profiles.exists():
            # Use existing organization
            organization = user_profiles.first().organization
        else:
            # Create personal organization
            organization, created = Organization.objects.get_or_create(
                name=f"{user.get_full_name() or user.username} (Personal)",
                defaults={
                    'organization_type': 'personal',
                    'description': 'Personal account',
                    'is_active': True
                }
            )
            
            # Create user profile
            UserProfile.objects.create(
                user=user,
                organization=organization,
                is_organization_admin=True
            )
        
        # Get or create personal free license
        try:
            service = Service.objects.get(slug=service_slug)
            license_type = service.license_types.get(name='personal_free')
            
            license, created = cls.objects.get_or_create(
                organization=organization,
                license_type=license_type,
                defaults={
                    'account_type': 'personal',
                    'is_personal_free': True,
                    'status': 'active',
                    'start_date': timezone.now(),
                    'created_by': user
                }
            )
            return license
        except (Service.DoesNotExist, LicenseType.DoesNotExist):
            return None


class LicenseUsageLog(models.Model):
    """
    Log of license usage for analytics and billing
    """
    license = models.ForeignKey(License, on_delete=models.CASCADE, related_name='usage_logs')
    
    # Usage snapshot
    users_count = models.PositiveIntegerField()
    projects_count = models.PositiveIntegerField()
    storage_gb = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Additional metrics
    api_calls = models.PositiveIntegerField(default=0)
    active_sessions = models.PositiveIntegerField(default=0)
    
    recorded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['license', 'recorded_at']),
        ]
        ordering = ['-recorded_at']
    
    def __str__(self):
        return f"{self.license} usage at {self.recorded_at}"
