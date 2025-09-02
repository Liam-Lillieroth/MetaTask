from django.db import models
from django.conf import settings
from decimal import Decimal


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
        ('free', 'Free'),
        ('basic', 'Basic'),
        ('professional', 'Professional'),
        ('enterprise', 'Enterprise'),
        ('custom', 'Custom'),
    ]
    
    name = models.CharField(max_length=50, choices=LICENSE_TYPES)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='license_types')
    
    # Pricing
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Limitations
    max_users = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum users allowed, null for unlimited")
    max_projects = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum projects allowed, null for unlimited")
    max_storage_gb = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum storage in GB, null for unlimited")
    
    # Features
    features = models.JSONField(default=list, help_text="List of included features")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['service', 'name']
        ordering = ['service', 'price_monthly']
    
    def __str__(self):
        return f"{self.service.name} - {self.get_name_display()}"


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
    ]
    
    BILLING_CYCLE_CHOICES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
        ('lifetime', 'Lifetime'),
    ]
    
    license_type = models.ForeignKey(LicenseType, on_delete=models.CASCADE)
    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE, related_name='licenses')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLE_CHOICES, default='monthly')
    
    # License period
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    
    # Current usage tracking
    current_users = models.PositiveIntegerField(default=0)
    current_projects = models.PositiveIntegerField(default=0)
    current_storage_gb = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
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
        ]
    
    def __str__(self):
        return f"{self.organization.name} - {self.license_type}"
    
    def is_valid(self):
        """Check if the license is currently valid"""
        from django.utils import timezone
        if self.status != 'active':
            return False
        if self.end_date and self.end_date < timezone.now():
            return False
        return True
    
    def usage_percentage(self, resource_type):
        """Calculate usage percentage for a given resource type"""
        if resource_type == 'users':
            max_val = self.license_type.max_users
            current_val = self.current_users
        elif resource_type == 'projects':
            max_val = self.license_type.max_projects
            current_val = self.current_projects
        elif resource_type == 'storage':
            max_val = self.license_type.max_storage_gb
            current_val = float(self.current_storage_gb)
        else:
            return 0
        
        if max_val is None:  # Unlimited
            return 0
        if max_val == 0:
            return 100
        
        return min(100, (current_val / max_val) * 100)


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
