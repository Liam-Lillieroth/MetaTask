from rest_framework import serializers
from .models import SchedulableResource, BookingRequest, ResourceScheduleRule


class SchedulableResourceSerializer(serializers.ModelSerializer):
    """Serializer for SchedulableResource"""
    
    linked_team_name = serializers.CharField(source='linked_team.name', read_only=True)
    
    class Meta:
        model = SchedulableResource
        fields = [
            'id', 'name', 'resource_type', 'description',
            'max_concurrent_bookings', 'default_booking_duration',
            'availability_rules', 'linked_team', 'linked_team_name',
            'external_resource_id', 'service_type', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class BookingRequestSerializer(serializers.ModelSerializer):
    """Serializer for BookingRequest"""
    
    resource_name = serializers.CharField(source='resource.name', read_only=True)
    requested_by_name = serializers.CharField(source='requested_by.get_display_name', read_only=True)
    completed_by_name = serializers.CharField(source='completed_by.get_display_name', read_only=True)
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = BookingRequest
        fields = [
            'id', 'uuid', 'title', 'description',
            'requested_start', 'requested_end', 'actual_start', 'actual_end',
            'resource', 'resource_name', 'required_capacity',
            'status', 'priority',
            'source_service', 'source_object_type', 'source_object_id',
            'requested_by', 'requested_by_name',
            'completed_by', 'completed_by_name',
            'custom_data', 'duration',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'uuid', 'actual_start', 'actual_end', 'requested_by',
            'completed_by', 'created_at', 'updated_at'
        ]
    
    def get_duration(self, obj):
        """Get the duration of the booking in hours"""
        duration = obj.duration()
        return duration.total_seconds() / 3600


class BookingRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating BookingRequest"""
    
    class Meta:
        model = BookingRequest
        fields = [
            'title', 'description',
            'requested_start', 'requested_end',
            'resource', 'required_capacity',
            'priority', 'custom_data'
        ]
    
    def validate(self, data):
        """Validate booking request data"""
        
        if data['requested_start'] >= data['requested_end']:
            raise serializers.ValidationError(
                "Requested start time must be before end time"
            )
        
        # Check if the time slot is available
        from .services import SchedulingService
        
        # Get organization from context (should be set in view)
        organization = self.context['request'].user.userprofile.organization
        scheduling_service = SchedulingService(organization)
        
        if not scheduling_service.is_time_slot_available(
            data['resource'],
            data['requested_start'],
            data['requested_end']
        ):
            raise serializers.ValidationError(
                "The requested time slot is not available"
            )
        
        return data


class ResourceScheduleRuleSerializer(serializers.ModelSerializer):
    """Serializer for ResourceScheduleRule"""
    
    resource_name = serializers.CharField(source='resource.name', read_only=True)
    
    class Meta:
        model = ResourceScheduleRule
        fields = [
            'id', 'resource', 'resource_name', 'rule_type',
            'name', 'description', 'rule_config',
            'effective_start', 'effective_end', 'priority',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class TeamBookingSyncSerializer(serializers.Serializer):
    """Serializer for syncing team bookings"""
    
    team_name = serializers.CharField()
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)


class BookingSuggestionSerializer(serializers.Serializer):
    """Serializer for booking time suggestions"""
    
    resource_id = serializers.IntegerField(required=False)
    team_name = serializers.CharField(required=False)
    preferred_start = serializers.DateTimeField()
    duration_hours = serializers.FloatField(default=2.0)
    max_alternatives = serializers.IntegerField(default=5)
    
    def validate(self, data):
        """Validate that either resource_id or team_name is provided"""
        
        if not data.get('resource_id') and not data.get('team_name'):
            raise serializers.ValidationError(
                "Either resource_id or team_name must be provided"
            )
        
        return data