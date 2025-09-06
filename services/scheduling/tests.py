from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta, date
from core.models import Organization, UserProfile
from .models import SchedulableResource, BookingRequest, ResourceScheduleRule
from .services import SchedulingService, ResourceManagementService
from .integrations import CFlowsIntegration

User = get_user_model()


class SchedulingServiceTest(TestCase):
    """Test cases for SchedulingService"""
    
    def setUp(self):
        """Set up test data"""
        # Create test organization
        self.organization = Organization.objects.create(
            name="Test Organization",
            organization_type="business"
        )
        
        # Create test user
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        
        self.user_profile = UserProfile.objects.create(
            user=self.user,
            organization=self.organization
        )
        
        # Create test resource
        self.resource = SchedulableResource.objects.create(
            organization=self.organization,
            name="Test Room",
            resource_type="room",
            description="A test meeting room",
            max_concurrent_bookings=1
        )
        
        self.scheduling_service = SchedulingService(self.organization)
    
    def test_create_booking(self):
        """Test successful booking creation"""
        start_time = timezone.now() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=2)
        
        booking = self.scheduling_service.create_booking(
            user_profile=self.user_profile,
            resource=self.resource,
            start_time=start_time,
            end_time=end_time,
            title="Test Booking"
        )
        
        self.assertIsNotNone(booking)
        self.assertEqual(booking.title, "Test Booking")
        self.assertEqual(booking.resource, self.resource)
        self.assertEqual(booking.requested_by, self.user_profile)
        self.assertEqual(booking.status, 'pending')
    
    def test_check_availability(self):
        """Test resource availability checking"""
        start_time = timezone.now() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=2)
        
        # Should be available initially
        self.assertTrue(
            self.scheduling_service.check_availability(self.resource, start_time, end_time)
        )
        
        # Create a booking
        BookingRequest.objects.create(
            organization=self.organization,
            title="Existing Booking",
            resource=self.resource,
            requested_start=start_time,
            requested_end=end_time,
            requested_by=self.user_profile,
            status='confirmed'
        )
        
        # Should not be available now
        self.assertFalse(
            self.scheduling_service.check_availability(self.resource, start_time, end_time)
        )
    
    def test_suggest_alternative_times(self):
        """Test alternative time suggestions"""
        preferred_start = timezone.now() + timedelta(hours=1)
        duration = timedelta(hours=2)
        
        # Block preferred time
        BookingRequest.objects.create(
            organization=self.organization,
            title="Blocking Booking",
            resource=self.resource,
            requested_start=preferred_start,
            requested_end=preferred_start + duration,
            requested_by=self.user_profile,
            status='confirmed'
        )
        
        suggestions = self.scheduling_service.suggest_alternative_times(
            self.resource, preferred_start, duration, max_alternatives=3
        )
        
        self.assertGreater(len(suggestions), 0)
        self.assertTrue(all('start_time' in s for s in suggestions))
        self.assertTrue(all('end_time' in s for s in suggestions))
        self.assertTrue(all('score' in s for s in suggestions))
    
    def test_booking_status_transitions(self):
        """Test booking status transitions"""
        booking = BookingRequest.objects.create(
            organization=self.organization,
            title="Test Booking",
            resource=self.resource,
            requested_start=timezone.now() + timedelta(hours=1),
            requested_end=timezone.now() + timedelta(hours=3),
            requested_by=self.user_profile,
            status='pending'
        )
        
        # Confirm booking
        success = self.scheduling_service.confirm_booking(booking, self.user_profile)
        self.assertTrue(success)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'confirmed')
        
        # Start booking
        success = self.scheduling_service.start_booking(booking, self.user_profile)
        self.assertTrue(success)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'in_progress')
        self.assertIsNotNone(booking.actual_start)
        
        # Complete booking
        success = self.scheduling_service.complete_booking(booking, self.user_profile)
        self.assertTrue(success)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'completed')
        self.assertIsNotNone(booking.actual_end)
        self.assertIsNotNone(booking.completed_at)
        self.assertEqual(booking.completed_by, self.user_profile)
    
    def test_get_upcoming_bookings(self):
        """Test retrieval of upcoming bookings"""
        # Create future booking
        BookingRequest.objects.create(
            organization=self.organization,
            title="Future Booking",
            resource=self.resource,
            requested_start=timezone.now() + timedelta(days=1),
            requested_end=timezone.now() + timedelta(days=1, hours=2),
            requested_by=self.user_profile,
            status='confirmed'
        )
        
        # Create past booking (should not be included)
        BookingRequest.objects.create(
            organization=self.organization,
            title="Past Booking",
            resource=self.resource,
            requested_start=timezone.now() - timedelta(days=1),
            requested_end=timezone.now() - timedelta(hours=22),
            requested_by=self.user_profile,
            status='completed'
        )
        
        upcoming = self.scheduling_service.get_upcoming_bookings(days=7)
        self.assertEqual(len(upcoming), 1)
        self.assertEqual(upcoming[0].title, "Future Booking")


class ResourceManagementServiceTest(TestCase):
    """Test cases for ResourceManagementService"""
    
    def setUp(self):
        """Set up test data"""
        self.organization = Organization.objects.create(
            name="Test Organization",
            organization_type="business"
        )
        
        self.resource_service = ResourceManagementService(self.organization)
    
    def test_create_resource(self):
        """Test resource creation"""
        resource = self.resource_service.create_resource(
            organization=self.organization,
            name="Test Equipment",
            resource_type="equipment",
            description="Test equipment description",
            capacity=2
        )
        
        self.assertIsNotNone(resource)
        self.assertEqual(resource.name, "Test Equipment")
        self.assertEqual(resource.resource_type, "equipment")
        self.assertEqual(resource.max_concurrent_bookings, 2)
        self.assertTrue(resource.is_active)
    
    def test_update_resource(self):
        """Test resource updates"""
        resource = SchedulableResource.objects.create(
            organization=self.organization,
            name="Original Name",
            resource_type="room",
            max_concurrent_bookings=1
        )
        
        updated = self.resource_service.update_resource(
            resource.id,
            name="Updated Name",
            max_concurrent_bookings=3
        )
        
        self.assertIsNotNone(updated)
        self.assertEqual(updated.name, "Updated Name")
        self.assertEqual(updated.max_concurrent_bookings, 3)
    
    def test_deactivate_resource_with_future_bookings(self):
        """Test resource deactivation when future bookings exist"""
        resource = SchedulableResource.objects.create(
            organization=self.organization,
            name="Test Resource",
            resource_type="room"
        )
        
        user = User.objects.create_user(username="testuser", email="test@example.com")
        user_profile = UserProfile.objects.create(user=user, organization=self.organization)
        
        # Create future booking
        BookingRequest.objects.create(
            organization=self.organization,
            title="Future Booking",
            resource=resource,
            requested_start=timezone.now() + timedelta(days=1),
            requested_end=timezone.now() + timedelta(days=1, hours=2),
            requested_by=user_profile,
            status='confirmed'
        )
        
        # Should not be able to deactivate
        success = self.resource_service.deactivate_resource(resource.id)
        self.assertFalse(success)
        
        resource.refresh_from_db()
        self.assertTrue(resource.is_active)


class SchedulingIntegrationsTest(TestCase):
    """Test cases for scheduling integrations"""
    
    def setUp(self):
        """Set up test data"""
        self.organization = Organization.objects.create(
            name="Test Organization",
            organization_type="business"
        )
        
        self.integration = CFlowsIntegration(self.organization)
    
    def test_get_booking_by_source(self):
        """Test finding bookings by source information"""
        user = User.objects.create_user(username="testuser", email="test@example.com")
        user_profile = UserProfile.objects.create(user=user, organization=self.organization)
        
        resource = SchedulableResource.objects.create(
            organization=self.organization,
            name="Test Resource",
            resource_type="team"
        )
        
        booking = BookingRequest.objects.create(
            organization=self.organization,
            title="Test Booking",
            resource=resource,
            requested_start=timezone.now() + timedelta(hours=1),
            requested_end=timezone.now() + timedelta(hours=3),
            requested_by=user_profile,
            source_service='cflows',
            source_object_type='team_booking',
            source_object_id='123'
        )
        
        found_booking = self.integration.get_booking_by_source(
            'cflows', 'team_booking', '123'
        )
        
        self.assertEqual(found_booking, booking)
        
        # Test with non-existent booking
        not_found = self.integration.get_booking_by_source(
            'cflows', 'team_booking', '999'
        )
        self.assertIsNone(not_found)
