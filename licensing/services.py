"""
Licensing service for managing user license assignments and permissions
"""
from django.utils import timezone
from django.db.models import Q
from .models import License, CustomLicense, UserLicenseAssignment, LicenseAuditLog, Service


class LicensingService:
    """Service class for managing licensing operations"""
    
    @staticmethod
    def get_user_services(user_profile):
        """Get all services that a user has license access to"""
        # Get all active license assignments for the user
        assignments = UserLicenseAssignment.objects.filter(
            user_profile=user_profile,
            is_active=True,
            license__status__in=['active', 'trial']
        ).select_related('license__license_type__service', 'license__custom_license__service')
        
        services = set()
        for assignment in assignments:
            if assignment.license.custom_license:
                # Custom license
                if assignment.license.custom_license.is_valid():
                    services.add(assignment.license.custom_license.service)
            else:
                # Standard license
                if assignment.license.is_valid():
                    services.add(assignment.license.license_type.service)
        
        return list(services)
    
    @staticmethod
    def has_service_access(user_profile, service_slug):
        """Check if a user has access to a specific service"""
        try:
            service = Service.objects.get(slug=service_slug, is_active=True)
        except Service.DoesNotExist:
            return False
        
        # Check for active license assignments
        assignments = UserLicenseAssignment.objects.filter(
            user_profile=user_profile,
            is_active=True,
            license__status__in=['active', 'trial']
        ).select_related('license__license_type__service', 'license__custom_license__service')
        
        for assignment in assignments:
            if assignment.license.custom_license:
                # Custom license
                if (assignment.license.custom_license.service == service and 
                    assignment.license.custom_license.is_valid()):
                    return True
            else:
                # Standard license
                if (assignment.license.license_type.service == service and 
                    assignment.license.is_valid()):
                    return True
        
        return False
    
    @staticmethod
    def assign_user_to_license(license, user_profile, assigned_by_user):
        """Assign a user to a license (custom or standard)"""
        # Check if license can accommodate another user
        if license.custom_license:
            if not license.custom_license.can_assign_user():
                return False, "No available seats in custom license"
        else:
            if not license.can_add_user():
                return False, "License user limit reached"
        
        # Check if user already has assignment for this service
        service = license.custom_license.service if license.custom_license else license.license_type.service
        existing_assignment = UserLicenseAssignment.objects.filter(
            user_profile=user_profile,
            is_active=True,
            license__license_type__service=service
        ).first()
        
        if existing_assignment:
            return False, f"User already has license for {service.name}"
        
        # Create assignment
        assignment = UserLicenseAssignment.objects.create(
            license=license,
            user_profile=user_profile,
            assigned_by=assigned_by_user,
            is_active=True
        )
        
        # Update license user count
        license.current_users += 1
        license.save(update_fields=['current_users'])
        
        # Create audit log
        LicenseAuditLog.objects.create(
            license=license,
            custom_license=license.custom_license,
            user_assignment=assignment,
            action='assign',
            performed_by=assigned_by_user,
            affected_user=user_profile,
            description=f'User assigned to {service.name} license',
            new_values={
                'user_id': str(user_profile.id),
                'service': service.name
            }
        )
        
        return True, assignment
    
    @staticmethod
    def revoke_user_license(assignment, revoked_by_user, reason=""):
        """Revoke a user's license assignment"""
        if not assignment.is_active:
            return False, "Assignment is already inactive"
        
        # Revoke assignment
        assignment.revoke(revoked_by_user)
        
        # Update license user count
        license = assignment.license
        if license.current_users > 0:
            license.current_users -= 1
            license.save(update_fields=['current_users'])
        
        # Create audit log
        service = license.custom_license.service if license.custom_license else license.license_type.service
        LicenseAuditLog.objects.create(
            license=license,
            custom_license=license.custom_license,
            user_assignment=assignment,
            action='revoke',
            performed_by=revoked_by_user,
            affected_user=assignment.user_profile,
            description=f'User license revoked for {service.name}' + (f': {reason}' if reason else ''),
            old_values={
                'user_id': str(assignment.user_profile.id),
                'service': service.name
            }
        )
        
        return True, "License revoked successfully"
    
    @staticmethod
    def get_organization_license_summary(organization):
        """Get a summary of all licenses for an organization"""
        summary = {
            'standard_licenses': [],
            'custom_licenses': [],
            'total_users': 0,
            'total_available_seats': 0
        }
        
        # Standard licenses
        standard_licenses = License.objects.filter(
            organization=organization,
            custom_license__isnull=True,
            status__in=['active', 'trial']
        ).select_related('license_type__service')
        
        for license in standard_licenses:
            assigned_users = UserLicenseAssignment.objects.filter(
                license=license,
                is_active=True
            ).count()
            
            max_users = license.license_type.max_users or float('inf')
            available_seats = max_users - assigned_users if max_users != float('inf') else float('inf')
            
            summary['standard_licenses'].append({
                'license': license,
                'service': license.license_type.service,
                'assigned_users': assigned_users,
                'max_users': max_users,
                'available_seats': available_seats
            })
            
            summary['total_users'] += assigned_users
            if available_seats != float('inf'):
                summary['total_available_seats'] += available_seats
        
        # Custom licenses
        custom_licenses = CustomLicense.objects.filter(
            organization=organization,
            is_active=True
        ).select_related('service')
        
        for custom_license in custom_licenses:
            license_instance = getattr(custom_license, 'license_instance', None)
            assigned_users = 0
            
            if license_instance:
                assigned_users = UserLicenseAssignment.objects.filter(
                    license=license_instance,
                    is_active=True
                ).count()
            
            available_seats = custom_license.remaining_seats()
            
            summary['custom_licenses'].append({
                'custom_license': custom_license,
                'license_instance': license_instance,
                'service': custom_license.service,
                'assigned_users': assigned_users,
                'max_users': custom_license.max_users,
                'available_seats': available_seats
            })
            
            summary['total_users'] += assigned_users
            summary['total_available_seats'] += available_seats
        
        return summary
    
    @staticmethod
    def get_available_licenses_for_user(organization, service=None):
        """Get licenses that have available seats for new user assignments"""
        available_licenses = []
        
        # Standard licenses
        standard_query = License.objects.filter(
            organization=organization,
            custom_license__isnull=True,
            status__in=['active', 'trial']
        ).select_related('license_type__service')
        
        if service:
            standard_query = standard_query.filter(license_type__service=service)
        
        for license in standard_query:
            if license.can_add_user():
                available_licenses.append({
                    'license': license,
                    'type': 'standard',
                    'service': license.license_type.service,
                    'available_seats': (license.license_type.max_users or float('inf')) - license.current_users
                })
        
        # Custom licenses
        custom_query = CustomLicense.objects.filter(
            organization=organization,
            is_active=True
        ).select_related('service', 'license_instance')
        
        if service:
            custom_query = custom_query.filter(service=service)
        
        for custom_license in custom_query:
            if custom_license.can_assign_user():
                license_instance = getattr(custom_license, 'license_instance', None)
                if license_instance:
                    available_licenses.append({
                        'license': license_instance,
                        'custom_license': custom_license,
                        'type': 'custom',
                        'service': custom_license.service,
                        'available_seats': custom_license.remaining_seats()
                    })
        
        return available_licenses


class LicenseDecorator:
    """Decorator for checking service access"""
    
    @staticmethod
    def require_service_license(service_slug):
        """Decorator to require license for a specific service"""
        def decorator(view_func):
            def wrapper(request, *args, **kwargs):
                if request.user.is_authenticated:
                    try:
                        user_profile = request.user.mediap_profile
                        if LicensingService.has_service_access(user_profile, service_slug):
                            return view_func(request, *args, **kwargs)
                    except:
                        pass
                
                # No access - redirect or show error
                from django.shortcuts import render
                return render(request, 'licensing/no_access.html', {
                    'service_slug': service_slug,
                    'required_service': service_slug
                })
            
            return wrapper
        return decorator
