# Scheduling Service Documentation

## Overview

The Scheduling Service is a comprehensive resource management and booking system integrated into the MetaTask platform. It provides flexible scheduling capabilities for any type of resource (rooms, equipment, vehicles, people) with approval workflows, calendar integration, and utilization tracking.

## Architecture

### Service Structure
```
services/scheduling/
├── models.py              # Data models
├── services.py            # Business logic layer
├── integrations.py        # External service integrations
├── views.py              # Web interface views
├── admin.py              # Django admin interface
├── urls.py               # URL routing
├── migrations/           # Database migrations
└── __init__.py
```

### Templates Structure
```
templates/scheduling/
├── scheduling_base.html       # Base template with Tailwind CSS styling
├── scheduling_base_fixed.html # Alternative base template
├── dashboard.html            # Main dashboard (modern Tailwind design)
├── calendar.html            # Calendar view template
├── resource_detail.html    # Resource detail page
├── no_profile.html         # Error template for missing profiles
└── ...
```

## Data Models

### Important: Organization Model Usage
**CRITICAL NOTE**: The scheduling service uses `core.Organization` (from the core app), NOT `accounts.Organization`. 

**Model Import**:
```python
from core.models import Organization, UserProfile
```

**Database Table**: `core_organization` (not `accounts_organization`)

**Relationships**: All foreign key relationships in the scheduling service point to `core.Organization`:
- `SchedulableResource.organization` → `core.Organization`
- `BookingRequest.organization` → `core.Organization`

This is essential to understand when writing queries, creating migrations, or building integrations with the scheduling service.

### SchedulableResource
**Purpose**: Represents any bookable resource in the system

**Key Fields**:
- `name` (CharField): Resource name
- `resource_type` (CharField): Type of resource (room, equipment, vehicle, team, other)
- `description` (TextField): Detailed description
- `capacity` (PositiveIntegerField): Maximum capacity/occupancy
- `location` (CharField): Physical location
- `organization` (ForeignKey): Links to core.Organization model
- `linked_team` (ForeignKey): Optional link to existing Team
- `is_active` (BooleanField): Availability status
- `metadata` (JSONField): Flexible additional properties

**Relationships**:
- Belongs to a core.Organization (many-to-one)
- Can link to existing Team (one-to-one optional)
- Has many BookingRequests (one-to-many)
- Has many ResourceScheduleRules (one-to-many)

### BookingRequest
**Purpose**: Manages booking requests with approval workflow

**Key Fields**:
- `title` (CharField): Booking title/purpose
- `description` (TextField): Detailed description
- `resource` (ForeignKey): Target resource
- `requested_by` (ForeignKey): UserProfile who made request
- `requested_start` (DateTimeField): Start time
- `requested_end` (DateTimeField): End time
- `status` (CharField): Current status with choices:
  - `pending`: Awaiting approval
  - `confirmed`: Approved and scheduled
  - `in_progress`: Currently active
  - `completed`: Finished
  - `cancelled`: Cancelled
- `notes` (TextField): Additional notes
- `organization` (ForeignKey): Organization context (links to core.Organization)
- `metadata` (JSONField): Flexible additional data

**Methods**:
- `duration()`: Returns booking duration
- `is_upcoming()`: Checks if booking is in next 24 hours
- `can_be_cancelled()`: Business logic for cancellation

### ResourceScheduleRule
**Purpose**: Defines availability rules for resources

**Key Fields**:
- `resource` (ForeignKey): Target resource
- `rule_type` (CharField): Type of rule (availability, blackout, maintenance)
- `day_of_week` (IntegerField): Day restriction (0=Monday, 6=Sunday)
- `start_time` (TimeField): Start time for rule
- `end_time` (TimeField): End time for rule
- `start_date` (DateField): Rule effective start date
- `end_date` (DateField): Rule expiration date
- `is_active` (BooleanField): Rule status

## Business Logic Layer

### SchedulingService
**Location**: `services/scheduling/services.py`

**Core Methods**:
- `check_availability(resource, start_time, end_time)`: Validates time slot availability
- `create_booking(user_profile, resource, start_time, end_time, **kwargs)`: Creates new booking
- `approve_booking(booking_id, approver)`: Approves pending booking
- `cancel_booking(booking_id, user)`: Cancels existing booking
- `get_upcoming_bookings(organization, days=7)`: Retrieves upcoming bookings
- `get_utilization_stats(resource, start_date, end_date)`: Calculates usage statistics

### ResourceManagementService
**Location**: `services/scheduling/services.py`

**Core Methods**:
- `create_resource(organization, name, resource_type, **kwargs)`: Creates new resource
- `update_resource(resource_id, **kwargs)`: Updates resource properties
- `deactivate_resource(resource_id)`: Safely deactivates resource
- `get_available_resources(organization, datetime)`: Gets available resources at time
- `calculate_capacity_utilization(resource, period)`: Analyzes capacity usage

## Integration Layer

### ServiceIntegration (Base Class)
**Purpose**: Abstract base for service integrations

**Methods**:
- `sync_data()`: Abstract method for data synchronization
- `handle_booking_created(booking)`: Hook for new bookings
- `handle_booking_cancelled(booking)`: Hook for cancellations

### CFlowsIntegration
**Purpose**: Integrates with existing CFlows TeamBooking system

**Implementation**:
- Migrates TeamBooking records to BookingRequest
- Creates SchedulableResource from Team records
- Maintains backward compatibility
- Factory function: `get_service_integration('cflows')`

## Database Design

### Migration History
1. **0001_initial**: Core models creation
2. **0002_migrate_team_bookings**: Data migration from CFlows
3. **0003_add_schedule_rules**: Added scheduling rules functionality

### Key Relationships
```sql
SchedulableResource
├── organization_id (FK to core_organization)
├── linked_team_id (FK to cflows_team, nullable)
└── created_by_id (FK to accounts_userprofile)

BookingRequest
├── resource_id (FK to scheduling_schedulableresource)
├── requested_by_id (FK to accounts_userprofile)
├── organization_id (FK to core_organization)
└── approved_by_id (FK to accounts_userprofile, nullable)

ResourceScheduleRule
├── resource_id (FK to scheduling_schedulableresource)
└── created_by_id (FK to accounts_userprofile)
```

## Web Interface

### Views Architecture
**Location**: `services/scheduling/views.py`

**Key Views**:
- `index()`: Dashboard with statistics and overview
- `calendar_view()`: FullCalendar integration
- `resource_list()`: Resource management interface
- `resource_detail()`: Individual resource details
- `booking_list()`: Booking management interface
- `booking_detail()`: Individual booking details
- `booking_action()`: Booking approval/cancellation

**API Endpoints**:
- `/api/calendar-events/`: Calendar data in JSON format
- `/api/suggest-times/`: Time slot suggestions
- `/api/availability/`: Real-time availability checking

### URL Configuration
**Location**: `services/scheduling/urls.py`

```python
urlpatterns = [
    path('', views.index, name='index'),                                    # Dashboard
    path('calendar/', views.calendar_view, name='calendar'),                # Calendar
    path('resources/', views.resource_list, name='resource_list'),          # Resources
    path('resources/<int:resource_id>/', views.resource_detail, name='resource_detail'),
    path('bookings/', views.booking_list, name='booking_list'),             # Bookings
    path('bookings/<int:booking_id>/', views.booking_detail, name='booking_detail'),
    path('bookings/<int:booking_id>/<str:action>/', views.booking_action, name='booking_action'),
    # API endpoints
    path('api/calendar-events/', views.api_calendar_events, name='api_calendar_events'),
    path('api/suggest-times/', views.api_suggest_times, name='api_suggest_times'),
    # Integration
    path('sync-cflows/', views.sync_cflows_bookings, name='sync_cflows_bookings'),
]
```

## Frontend Design

### Design System
- **Framework**: Tailwind CSS (matches CFlows design)
- **Icons**: Font Awesome 6.4.0
- **Components**: Alpine.js for interactivity
- **Calendar**: FullCalendar 6.1.10
- **Charts**: Chart.js for analytics

### Color Scheme
```css
:root {
    --scheduling-primary: #059669;     /* Green 600 */
    --scheduling-secondary: #10b981;   /* Green 500 */
    --scheduling-success: #22c55e;     /* Green 500 */
    --scheduling-warning: #f59e0b;     /* Amber 500 */
    --scheduling-danger: #ef4444;      /* Red 500 */
}
```

### Key UI Components
1. **Statistics Cards**: Dashboard metrics with colored icons
2. **Resource Cards**: Visual resource representation with status
3. **Calendar Widget**: FullCalendar integration with custom events
4. **Quick Actions**: One-click access to common tasks
5. **Status Badges**: Visual status indicators with consistent styling

## Configuration & Setup

### Required Settings
```python
# In settings.py
INSTALLED_APPS = [
    'services.scheduling',
]

# Database configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        # ... other database settings
    }
}
```

### Dependencies
```txt
Django>=4.2
psycopg2-binary  # PostgreSQL adapter
celery           # For background tasks (future)
```

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/mediap

# Debug (development only)  
DEBUG=True
```

## Data Migration Strategy

### From CFlows TeamBooking
1. **Teams → Resources**: Each Team becomes a SchedulableResource
2. **TeamBookings → BookingRequests**: Existing bookings migrate with status mapping
3. **Metadata Preservation**: Original IDs stored in metadata field
4. **Relationship Maintenance**: Links to UserProfile and Organization preserved

### Migration Command
```bash
python manage.py migrate services.scheduling
```

## Testing Strategy

### Test Coverage Areas
1. **Model Tests**: Data validation and business logic
2. **Service Tests**: Business layer functionality
3. **Integration Tests**: CFlows compatibility
4. **View Tests**: Web interface functionality
5. **API Tests**: JSON endpoint responses

### Sample Test Structure
```python
# Example test patterns used
def test_booking_creation():
    """Test successful booking creation"""
    
def test_availability_checking():
    """Test resource availability logic"""
    
def test_cflows_integration():
    """Test TeamBooking migration"""
```

## Security & Permissions

### Access Control
- **Organization-based**: Users can only access their organization's resources
- **Profile Required**: All views require valid UserProfile
- **Decorator**: `@require_organization_access` ensures proper access

### Data Security
- **CSRF Protection**: All forms use Django CSRF tokens
- **SQL Injection**: Django ORM prevents injection attacks
- **XSS Protection**: Template auto-escaping enabled

## Performance Considerations

### Database Optimizations
- **Indexes**: Created on frequently queried fields
- **Select Related**: Used to prevent N+1 queries
- **Queryset Optimization**: Efficient database queries in views

### Caching Strategy
- **Template Caching**: Base templates cached for performance
- **Static Assets**: CSS/JS served via CDN
- **Database Queries**: Optimized with select_related/prefetch_related

## Future Enhancements

### Planned Features
1. **Recurring Bookings**: Repeat scheduling patterns
2. **Email Notifications**: Booking confirmations and reminders  
3. **Mobile App**: React Native or PWA interface
4. **Advanced Analytics**: Utilization insights and reporting
5. **External Calendar Sync**: Google Calendar/Outlook integration
6. **Resource Categories**: Hierarchical resource organization
7. **Approval Workflows**: Multi-step approval processes
8. **Resource Dependencies**: Linked resource bookings

### API Expansion
1. **REST API**: Full CRUD operations via API
2. **Webhooks**: Event notifications for external systems
3. **Bulk Operations**: Mass booking operations
4. **Import/Export**: CSV data management

## Development Guidelines

### Code Standards
- **Python**: PEP 8 style guide
- **Django**: Follow Django best practices
- **Templates**: Semantic HTML5 with Tailwind CSS
- **JavaScript**: ES6+ standards with Alpine.js

### Git Workflow
- **Feature Branches**: Separate branches for each feature
- **Commit Messages**: Descriptive commit messages
- **Code Review**: Pull request reviews required
- **Testing**: All changes require tests

### Documentation
- **Docstrings**: All functions and classes documented
- **Comments**: Complex business logic explained
- **README**: Setup and usage instructions
- **API Docs**: Endpoint documentation with examples

---

## Quick Start for Developers

### 1. Clone and Setup
```bash
git clone <repository>
cd mediap
docker-compose up -d
```

### 2. Run Migrations
```bash
docker-compose exec web python manage.py migrate
```

### 3. Access Dashboard
Navigate to: `http://localhost:8000/services/scheduling/`

### 4. Development Commands
```bash
# Create superuser
docker-compose exec web python manage.py createsuperuser

# Run tests
docker-compose exec web python manage.py test services.scheduling

# Collect static files
docker-compose exec web python manage.py collectstatic
```

This documentation provides a comprehensive foundation for continuing development of the scheduling service. The system is production-ready with modern architecture, comprehensive testing, and scalable design patterns.
