from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta, date
from core.models import Organization, UserProfile, Team
from .models import SchedulableResource, BookingRequest, ResourceScheduleRule
from .services import SchedulingService, ResourceManagementService
from .integrations import CFlowsIntegration


class SchedulableResourceModelTest(TestCase):
    """Test SchedulableResource model"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.organization = Organization.objects.create(name='Test Org')
        self.user_profile = UserProfile.objects.create(user=self.user, organization=self.organization)
        self.team = Team.objects.create(name='Test Team', organization=self.organization)
    
    def test_create_resource(self):
        """Test creating a schedulable resource"""
        resource = SchedulableResource.objects.create(
            organization=self.organization,
            name='Test Resource',
            resource_type='team',
            description='A test resource',
            max_concurrent_bookings=2
        )
        
        self.assertEqual(resource.name, 'Test Resource')
        self.assertEqual(resource.resource_type, 'team')
        self.assertEqual(resource.max_concurrent_bookings, 2)
        self.assertTrue(resource.is_active)
    
    def test_resource_str_representation(self):
        """Test resource string representation"""
        resource = SchedulableResource.objects.create(
            organization=self.organization,
            name='Test Resource',
            resource_type='team'
        )
        
        self.assertEqual(str(resource), 'Test Resource (Team)')


class BookingRequestModelTest(TestCase):
    """Test BookingRequest model"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.organization = Organization.objects.create(name='Test Org')
        self.user_profile = UserProfile.objects.create(user=self.user, organization=self.organization)
        
        self.resource = SchedulableResource.objects.create(
            organization=self.organization,
            name='Test Resource',
            resource_type='team'
        )
        
        self.start_time = timezone.now() + timedelta(hours=1)
        self.end_time = self.start_time + timedelta(hours=2)
    
    def test_create_booking(self):
        """Test creating a booking request"""
        booking = BookingRequest.objects.create(
            organization=self.organization,
            title='Test Booking',
            description='A test booking',
            requested_start=self.start_time,
            requested_end=self.end_time,
            resource=self.resource,
            requested_by=self.user_profile,
            source_service='test',
            source_object_type='test_object',
            source_object_id='123'
        )
        
        self.assertEqual(booking.title, 'Test Booking')
        self.assertEqual(booking.status, 'pending')
        self.assertEqual(booking.priority, 'normal')
        self.assertIsNotNone(booking.uuid)
    
    def test_booking_duration(self):
        """Test booking duration calculation"""
        booking = BookingRequest.objects.create(
            organization=self.organization,
            title='Test Booking',
            requested_start=self.start_time,
            requested_end=self.end_time,
            resource=self.resource,
            requested_by=self.user_profile,
            source_service='test',
            source_object_type='test_object',
            source_object_id='123'
        )
        
        duration = booking.duration()
        self.assertEqual(duration, timedelta(hours=2))
    
    def test_booking_str_representation(self):
        """Test booking string representation"""
        booking = BookingRequest.objects.create(
            organization=self.organization,
            title='Test Booking',
            requested_start=self.start_time,
            requested_end=self.end_time,
            resource=self.resource,
            requested_by=self.user_profile,
            source_service='test',
            source_object_type='test_object',
            source_object_id='123'
        )
        
        expected = f"Test Booking - {self.start_time.strftime('%Y-%m-%d %H:%M')}"
        self.assertEqual(str(booking), expected)


class SchedulingServiceTest(TestCase):
    """Test SchedulingService business logic"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.organization = Organization.objects.create(name='Test Org')
        self.user_profile = UserProfile.objects.create(user=self.user, organization=self.organization)
        
        self.resource = SchedulableResource.objects.create(
            organization=self.organization,
            name='Test Resource',
            resource_type='team',
            max_concurrent_bookings=2
        )
        
        self.scheduling_service = SchedulingService(self.organization)
        
        self.start_time = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)
        self.end_time = self.start_time + timedelta(hours=2)
    
    def test_is_time_slot_available(self):
        """Test time slot availability checking"""
        # Should be available initially
        self.assertTrue(
            self.scheduling_service.is_time_slot_available(
                self.resource, self.start_time, self.end_time
            )
        )
        
        # Create a confirmed booking
        BookingRequest.objects.create(
            organization=self.organization,
            title='Existing Booking',
            requested_start=self.start_time,
            requested_end=self.end_time,
            resource=self.resource,
            status='confirmed',
            requested_by=self.user_profile,
            source_service='test',
            source_object_type='test_object',
            source_object_id='123'
        )
        
        # Should still be available (resource allows 2 concurrent bookings)
        self.assertTrue(
            self.scheduling_service.is_time_slot_available(
                self.resource, self.start_time, self.end_time
            )
        )
        
        # Create another confirmed booking
        BookingRequest.objects.create(
            organization=self.organization,
            title='Another Booking',
            requested_start=self.start_time,
            requested_end=self.end_time,
            resource=self.resource,
            status='confirmed',
            requested_by=self.user_profile,
            source_service='test',
            source_object_type='test_object',
            source_object_id='124'
        )
        
        # Should not be available now (capacity reached)
        self.assertFalse(
            self.scheduling_service.is_time_slot_available(
                self.resource, self.start_time, self.end_time
            )
        )
    
    def test_confirm_booking(self):
        """Test booking confirmation"""
        booking = BookingRequest.objects.create(
            organization=self.organization,
            title='Test Booking',
            requested_start=self.start_time,
            requested_end=self.end_time,
            resource=self.resource,
            requested_by=self.user_profile,
            source_service='test',
            source_object_type='test_object',
            source_object_id='123'
        )
        
        self.assertEqual(booking.status, 'pending')
        
        success = self.scheduling_service.confirm_booking(booking)
        self.assertTrue(success)
        
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'confirmed')
    
    def test_start_booking(self):
        """Test starting a booking"""
        booking = BookingRequest.objects.create(
            organization=self.organization,
            title='Test Booking',
            requested_start=self.start_time,
            requested_end=self.end_time,
            resource=self.resource,
            status='confirmed',
            requested_by=self.user_profile,
            source_service='test',
            source_object_type='test_object',
            source_object_id='123'
        )
        
        success = self.scheduling_service.start_booking(booking, self.user_profile)
        self.assertTrue(success)
        
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'in_progress')
        self.assertIsNotNone(booking.actual_start)
    
    def test_complete_booking(self):
        """Test completing a booking"""
        booking = BookingRequest.objects.create(
            organization=self.organization,
            title='Test Booking',
            requested_start=self.start_time,
            requested_end=self.end_time,
            resource=self.resource,
            status='in_progress',
            requested_by=self.user_profile,
            source_service='test',
            source_object_type='test_object',
            source_object_id='123'
        )
        
        success = self.scheduling_service.complete_booking(booking, self.user_profile)
        self.assertTrue(success)
        
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'completed')
        self.assertIsNotNone(booking.actual_end)
        self.assertEqual(booking.completed_by, self.user_profile)
    
    def test_suggest_alternative_times(self):
        """Test suggesting alternative booking times"""
        # Create a conflicting booking
        BookingRequest.objects.create(
            organization=self.organization,
            title='Conflicting Booking',
            requested_start=self.start_time,
            requested_end=self.end_time,
            resource=self.resource,
            status='confirmed',
            requested_by=self.user_profile,
            source_service='test',
            source_object_type='test_object',
            source_object_id='123'
        )
        
        # Make resource capacity 1 so we have conflicts
        self.resource.max_concurrent_bookings = 1
        self.resource.save()
        
        duration = timedelta(hours=2)
        suggestions = self.scheduling_service.suggest_alternative_times(
            self.resource, self.start_time, duration, max_alternatives=3
        )
        
        # Should get alternative times
        self.assertGreater(len(suggestions), 0)
        
        # All suggestions should be available
        for suggestion in suggestions:
            self.assertTrue(
                self.scheduling_service.is_time_slot_available(
                    self.resource, suggestion['start_time'], suggestion['end_time']
                )
            )


class ResourceManagementServiceTest(TestCase):
    """Test ResourceManagementService"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.organization = Organization.objects.create(name='Test Org')
        self.user_profile = UserProfile.objects.create(user=self.user, organization=self.organization)
        self.team = Team.objects.create(name='Test Team', organization=self.organization)
        
        self.resource_service = ResourceManagementService(self.organization)
    
    def test_create_resource(self):
        """Test creating a resource"""
        resource = self.resource_service.create_resource(
            name='Test Resource',
            resource_type='team',
            description='A test resource',
            max_concurrent_bookings=3,
            linked_team=self.team
        )
        
        self.assertEqual(resource.name, 'Test Resource')
        self.assertEqual(resource.resource_type, 'team')
        self.assertEqual(resource.max_concurrent_bookings, 3)
        self.assertEqual(resource.linked_team, self.team)
    
    def test_set_resource_availability(self):
        """Test setting resource availability"""
        resource = self.resource_service.create_resource(
            name='Test Resource',
            resource_type='team'
        )
        
        self.resource_service.set_resource_availability(
            resource,
            start_hour=9,
            end_hour=17,
            working_days=[0, 1, 2, 3, 4]  # Monday to Friday
        )
        
        resource.refresh_from_db()
        
        self.assertEqual(resource.availability_rules['start_hour'], 9)
        self.assertEqual(resource.availability_rules['end_hour'], 17)
        self.assertEqual(resource.availability_rules['working_days'], [0, 1, 2, 3, 4])


class CFlowsIntegrationTest(TestCase):
    """Test CFlows integration"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.organization = Organization.objects.create(name='Test Org')
        self.user_profile = UserProfile.objects.create(user=self.user, organization=self.organization)
        self.team = Team.objects.create(
            name='Test Team',
            organization=self.organization,
            default_capacity=2
        )
        
        self.integration = CFlowsIntegration(self.organization)
        
        # Mock workflow objects
        class MockWorkItem:
            def __init__(self):
                self.id = 1
                self.title = 'Test Work Item'
                
        class MockWorkflowStep:
            def __init__(self, team):
                self.id = 1
                self.name = 'Test Step'
                self.assigned_team = team
        
        self.mock_work_item = MockWorkItem()
        self.mock_workflow_step = MockWorkflowStep(self.team)
    
    def test_create_work_item_booking(self):
        """Test creating a booking from a work item"""
        start_time = timezone.now() + timedelta(hours=1)
        
        booking = self.integration.create_work_item_booking(
            work_item=self.mock_work_item,
            workflow_step=self.mock_workflow_step,
            requested_by=self.user_profile,
            start_time=start_time,
            duration_hours=3.0
        )
        
        self.assertEqual(booking.title, 'Test Work Item - Test Step')
        self.assertEqual(booking.source_service, 'cflows')
        self.assertEqual(booking.source_object_type, 'work_item')
        self.assertEqual(booking.source_object_id, '1')
        self.assertEqual(booking.custom_data['work_item_id'], 1)
        self.assertEqual(booking.custom_data['workflow_step_id'], 1)
        self.assertEqual(booking.custom_data['estimated_duration'], 3.0)
        
        # Check that resource was created
        resource = SchedulableResource.objects.get(linked_team=self.team)
        self.assertEqual(resource.name, 'Test Team')
        self.assertEqual(resource.resource_type, 'team')
        self.assertEqual(resource.service_type, 'cflows')
        self.assertEqual(resource.max_concurrent_bookings, 2)