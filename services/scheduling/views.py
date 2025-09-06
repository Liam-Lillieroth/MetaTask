from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime, parse_date
from datetime import datetime, timedelta
from .models import SchedulableResource, BookingRequest, ResourceScheduleRule
from .services import SchedulingService, ResourceManagementService
from .integrations import get_service_integration
from .serializers import (
    SchedulableResourceSerializer,
    BookingRequestSerializer,
    ResourceScheduleRuleSerializer,
    BookingRequestCreateSerializer
)


class SchedulableResourceViewSet(viewsets.ModelViewSet):
    """ViewSet for managing schedulable resources"""
    serializer_class = SchedulableResourceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return SchedulableResource.objects.filter(
            organization=self.request.user.userprofile.organization,
            is_active=True
        ).order_by('name')
    
    @action(detail=True, methods=['get'])
    def availability(self, request, pk=None):
        """Get availability for a resource"""
        resource = self.get_object()
        
        start_date = parse_date(request.query_params.get('start_date'))
        end_date = parse_date(request.query_params.get('end_date'))
        
        if not start_date or not end_date:
            return Response(
                {'error': 'start_date and end_date parameters are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        scheduling_service = SchedulingService(request.user.userprofile.organization)
        availability = scheduling_service.get_resource_availability(resource, start_date, end_date)
        
        return Response(availability)
    
    @action(detail=True, methods=['get'])
    def schedule(self, request, pk=None):
        """Get schedule for a resource"""
        resource = self.get_object()
        
        start_datetime = parse_datetime(request.query_params.get('start_datetime'))
        end_datetime = parse_datetime(request.query_params.get('end_datetime'))
        
        if not start_datetime or not end_datetime:
            return Response(
                {'error': 'start_datetime and end_datetime parameters are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        scheduling_service = SchedulingService(request.user.userprofile.organization)
        schedule = scheduling_service.get_resource_schedule(resource, start_datetime, end_datetime)
        
        return Response(schedule)
    
    @action(detail=True, methods=['post'])
    def suggest_times(self, request, pk=None):
        """Suggest alternative booking times"""
        resource = self.get_object()
        
        preferred_start = parse_datetime(request.data.get('preferred_start'))
        duration_hours = float(request.data.get('duration_hours', 2.0))
        max_alternatives = int(request.data.get('max_alternatives', 5))
        
        if not preferred_start:
            return Response(
                {'error': 'preferred_start is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        scheduling_service = SchedulingService(request.user.userprofile.organization)
        duration = timedelta(hours=duration_hours)
        suggestions = scheduling_service.suggest_alternative_times(
            resource, preferred_start, duration, max_alternatives
        )
        
        return Response(suggestions)


class BookingRequestViewSet(viewsets.ModelViewSet):
    """ViewSet for managing booking requests"""
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return BookingRequestCreateSerializer
        return BookingRequestSerializer
    
    def get_queryset(self):
        queryset = BookingRequest.objects.filter(
            organization=self.request.user.userprofile.organization
        ).select_related('resource', 'requested_by', 'completed_by').order_by('-requested_start')
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by resource
        resource_id = self.request.query_params.get('resource')
        if resource_id:
            queryset = queryset.filter(resource_id=resource_id)
        
        # Filter by date range
        start_date = parse_date(self.request.query_params.get('start_date'))
        end_date = parse_date(self.request.query_params.get('end_date'))
        
        if start_date:
            queryset = queryset.filter(requested_start__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(requested_start__date__lte=end_date)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.user.userprofile.organization,
            requested_by=self.request.user.userprofile
        )
    
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirm a pending booking"""
        booking = self.get_object()
        
        scheduling_service = SchedulingService(request.user.userprofile.organization)
        success = scheduling_service.confirm_booking(booking, request.user.userprofile)
        
        if success:
            serializer = self.get_serializer(booking)
            return Response(serializer.data)
        else:
            return Response(
                {'error': 'Could not confirm booking'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start a confirmed booking"""
        booking = self.get_object()
        
        scheduling_service = SchedulingService(request.user.userprofile.organization)
        success = scheduling_service.start_booking(booking, request.user.userprofile)
        
        if success:
            serializer = self.get_serializer(booking)
            return Response(serializer.data)
        else:
            return Response(
                {'error': 'Could not start booking'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete a booking"""
        booking = self.get_object()
        
        scheduling_service = SchedulingService(request.user.userprofile.organization)
        success = scheduling_service.complete_booking(booking, request.user.userprofile)
        
        if success:
            serializer = self.get_serializer(booking)
            return Response(serializer.data)
        else:
            return Response(
                {'error': 'Could not complete booking'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a booking"""
        booking = self.get_object()
        
        scheduling_service = SchedulingService(request.user.userprofile.organization)
        success = scheduling_service.cancel_booking(booking, request.user.userprofile)
        
        if success:
            serializer = self.get_serializer(booking)
            return Response(serializer.data)
        else:
            return Response(
                {'error': 'Could not cancel booking'},
                status=status.HTTP_400_BAD_REQUEST
            )


class ResourceScheduleRuleViewSet(viewsets.ModelViewSet):
    """ViewSet for managing resource schedule rules"""
    serializer_class = ResourceScheduleRuleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return ResourceScheduleRule.objects.filter(
            resource__organization=self.request.user.userprofile.organization
        ).select_related('resource').order_by('resource', 'rule_type', 'priority')


class IntegrationViewSet(viewsets.ViewSet):
    """ViewSet for service integrations"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def cflows_sync(self, request):
        """Sync CFlows team bookings to scheduling system"""
        
        integration = get_service_integration(
            request.user.userprofile.organization,
            'cflows'
        )
        
        synced_bookings = integration.sync_all_team_bookings()
        
        return Response({
            'synced_count': len(synced_bookings),
            'synced_bookings': [
                {
                    'id': booking.id,
                    'uuid': str(booking.uuid),
                    'title': booking.title,
                    'status': booking.status
                }
                for booking in synced_bookings
            ]
        })
    
    @action(detail=False, methods=['get'])
    def cflows_team_schedule(self, request):
        """Get schedule for a CFlows team"""
        
        team_name = request.query_params.get('team_name')
        start_datetime = parse_datetime(request.query_params.get('start_datetime'))
        end_datetime = parse_datetime(request.query_params.get('end_datetime'))
        
        if not team_name or not start_datetime or not end_datetime:
            return Response(
                {'error': 'team_name, start_datetime, and end_datetime are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        integration = get_service_integration(
            request.user.userprofile.organization,
            'cflows'
        )
        
        schedule = integration.get_team_schedule(team_name, start_datetime, end_datetime)
        
        return Response(schedule)
    
    @action(detail=False, methods=['post'])
    def cflows_suggest_times(self, request):
        """Suggest booking times for a CFlows team"""
        
        team_name = request.data.get('team_name')
        preferred_start = parse_datetime(request.data.get('preferred_start'))
        duration_hours = float(request.data.get('duration_hours', 2.0))
        max_alternatives = int(request.data.get('max_alternatives', 5))
        
        if not team_name or not preferred_start:
            return Response(
                {'error': 'team_name and preferred_start are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        integration = get_service_integration(
            request.user.userprofile.organization,
            'cflows'
        )
        
        suggestions = integration.suggest_booking_times(
            team_name, preferred_start, duration_hours, max_alternatives
        )
        
        return Response(suggestions)