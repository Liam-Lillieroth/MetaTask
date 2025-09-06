# Scheduling Service Documentation

The scheduling service is now fully operational and provides comprehensive resource booking and scheduling capabilities with flexible integration support for the CFlows service.

## Overview

The scheduling service is built as a Django app that provides:

- **Flexible Resource Management**: Support for teams, equipment, rooms, and custom resource types
- **Comprehensive Booking System**: Full lifecycle management from request to completion
- **CFlows Integration**: Seamless integration with the existing CFlows workflow system
- **REST API**: Complete API for all operations
- **Rule-Based Scheduling**: Configurable rules for availability, approval, and capacity
- **Management Tools**: Commands for setup and synchronization

## Core Components

### Models

1. **SchedulableResource**
   - Generic resource that can be scheduled (teams, equipment, rooms, etc.)
   - Configurable capacity and availability rules
   - Integration with CFlows teams
   - JSON-based availability configuration for flexibility

2. **BookingRequest**
   - Central booking entity with complete lifecycle management
   - Status tracking: pending → confirmed → in_progress → completed
   - Source service integration (tracks which service created the booking)
   - Custom data storage for service-specific requirements
   - Priority-based scheduling support

3. **ResourceScheduleRule**
   - Flexible rule system for scheduling constraints
   - Rule types: availability, blackout, auto_approval, require_approval, capacity_limit
   - JSON-based configuration for rule-specific settings
   - Priority-based rule application

### Services

1. **SchedulingService**
   - Core business logic for scheduling operations
   - Availability checking and conflict resolution
   - Alternative time suggestions
   - Booking lifecycle management
   - Utilization statistics and reporting

2. **ResourceManagementService**
   - Resource creation and configuration
   - Availability rule management
   - Blackout period management

3. **CFlowsIntegration**
   - Bidirectional integration with CFlows service
   - Automatic resource creation from teams
   - TeamBooking synchronization
   - Work item booking creation
   - Team schedule and availability queries

## API Endpoints

### Resources
- `GET /scheduling/api/resources/` - List all resources
- `POST /scheduling/api/resources/` - Create new resource
- `GET /scheduling/api/resources/{id}/` - Get resource details
- `GET /scheduling/api/resources/{id}/availability/` - Get availability data
- `GET /scheduling/api/resources/{id}/schedule/` - Get schedule in time range
- `POST /scheduling/api/resources/{id}/suggest_times/` - Suggest alternative times

### Bookings
- `GET /scheduling/api/bookings/` - List bookings (with filters)
- `POST /scheduling/api/bookings/` - Create new booking
- `GET /scheduling/api/bookings/{id}/` - Get booking details
- `POST /scheduling/api/bookings/{id}/confirm/` - Confirm pending booking
- `POST /scheduling/api/bookings/{id}/start/` - Start confirmed booking
- `POST /scheduling/api/bookings/{id}/complete/` - Complete booking
- `POST /scheduling/api/bookings/{id}/cancel/` - Cancel booking

### CFlows Integration
- `POST /scheduling/api/integrations/cflows_sync/` - Sync all CFlows bookings
- `GET /scheduling/api/integrations/cflows_team_schedule/` - Get team schedule
- `POST /scheduling/api/integrations/cflows_suggest_times/` - Suggest times for team

## Management Commands

### Setup Resources
```bash
python manage.py setup_scheduling_resources [--org-id ORG_ID]
```
- Creates schedulable resources for all teams
- Sets up default availability rules (9 AM - 5 PM, Monday-Friday)
- Links resources to CFlows teams

### Sync CFlows Bookings
```bash
python manage.py sync_cflows_bookings [--org-id ORG_ID]
```
- Synchronizes existing CFlows TeamBookings
- Creates corresponding BookingRequest entries
- Maintains data consistency between systems

## CFlows Integration Features

### Automatic Resource Creation
- When a booking is created for a team, a corresponding SchedulableResource is automatically created
- Resource inherits team capacity and settings
- Linked to the original team for bidirectional updates

### Work Item Booking Workflow
1. CFlows workflow step requires team capacity
2. Integration creates BookingRequest with work item context
3. System checks availability and applies rules
4. Auto-confirmation if rules allow
5. Status updates flow back to CFlows

### Team Booking Synchronization
- Existing CFlows TeamBookings can be synchronized to the new system
- Maintains all original data in custom_data field
- Status mapping between systems
- Assigned team members carried over

### Capacity Planning
- Teams can view their booking schedule
- Utilization statistics and reporting
- Availability checking for planning
- Alternative time suggestions for optimization

## Configuration Examples

### Setting Resource Availability
```python
from services.scheduling.services import ResourceManagementService

resource_service = ResourceManagementService(organization)
resource_service.set_resource_availability(
    resource,
    start_hour=8,      # 8 AM
    end_hour=18,       # 6 PM
    working_days=[0, 1, 2, 3, 4]  # Monday to Friday
)
```

### Creating Blackout Periods
```python
resource_service.add_blackout_period(
    resource,
    start_time=datetime(2024, 12, 25, 0, 0),  # Christmas Day
    end_time=datetime(2024, 12, 25, 23, 59),
    name="Christmas Holiday",
    description="Office closed for Christmas"
)
```

### Auto-Approval Rules
```python
from services.scheduling.models import ResourceScheduleRule

rule = ResourceScheduleRule.objects.create(
    resource=resource,
    rule_type='auto_approval',
    name='Short Duration Auto-Approval',
    rule_config={
        'max_duration_hours': 2,
        'min_priority': 'normal'
    }
)
```

## Integration Usage Examples

### Creating a Work Item Booking
```python
from services.scheduling.integrations import CFlowsIntegration

integration = CFlowsIntegration(organization)
booking = integration.create_work_item_booking(
    work_item=work_item,
    workflow_step=workflow_step,
    requested_by=user_profile,
    start_time=datetime.now() + timedelta(hours=2),
    duration_hours=3.0,
    custom_data={'project_id': 'PROJ-123'}
)
```

### Getting Team Availability
```python
availability = integration.get_team_availability(
    team_name='Development Team',
    start_date=date.today(),
    end_date=date.today() + timedelta(days=7)
)
```

### Suggesting Alternative Times
```python
suggestions = integration.suggest_booking_times(
    team_name='Development Team',
    preferred_start=datetime.now() + timedelta(hours=1),
    duration_hours=2.0,
    max_alternatives=5
)
```

## Key Benefits

1. **Flexible and Extensible**: JSON-based configuration allows for future enhancements without schema changes
2. **Service Agnostic**: While integrated with CFlows, can work with any service
3. **Complete Lifecycle Management**: Handles entire booking process from creation to completion
4. **Intelligent Scheduling**: Provides suggestions and conflict resolution
5. **Audit Trail**: Complete history of booking changes and status updates
6. **Scalable**: Efficient database design with proper indexing
7. **Admin Friendly**: Complete Django admin interface for management

## Installation and Setup

1. **Add to Django Settings**
   ```python
   INSTALLED_APPS = [
       # ... other apps
       'services.scheduling',
   ]
   ```

2. **Include URLs**
   ```python
   urlpatterns = [
       # ... other patterns
       path('scheduling/', include('services.scheduling.urls')),
   ]
   ```

3. **Run Migrations**
   ```bash
   python manage.py makemigrations scheduling
   python manage.py migrate
   ```

4. **Setup Resources**
   ```bash
   python manage.py setup_scheduling_resources
   ```

5. **Sync Existing Data** (if applicable)
   ```bash
   python manage.py sync_cflows_bookings
   ```

The scheduling service is now ready for production use and provides a comprehensive, flexible solution for resource booking and scheduling with excellent CFlows integration capabilities.