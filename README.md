# Mediap Project Specification

## Project Overview
**Project Name:** Mediap
**Date:** 2025-09-02
**Owner:** @LiamOlsson

Mediap is a comprehensive service application designed to streamline workflows for organizations, small teams, companies, and individuals. It integrates multiple services including workflow management (cflows) and job planning functionality. The platform will offer various services with licensing options and a homepage showcasing available products.

## Existing Repositories

### cflows-by-mediap
Based on repository content, this system appears to be:
- A workflow management system for organizations
- Designed to help teams visualize and manage complex business processes
- Features likely include:
  - Workflow creation and customization
  - Task assignment and tracking
  - Status monitoring and reporting
  - Process automation tools
  - Approval chains and checkpoints
  - Visualization of process flows
- Built with Django framework
- Currently operates as a standalone service

### mediap-job-planning
Based on repository content, this system appears to be:
- A job and task planning solution
- Designed for resource allocation and scheduling
- Features likely include:
  - Project management capabilities
  - Resource scheduling and allocation
  - Task assignment and deadline tracking
  - Time management tools
  - Status reporting and analytics
  - Calendar integration
- Built with Django framework
- Currently operates as a standalone service

## Technical Stack

### Backend
- **Framework:** Django
- **API:** Django REST Framework
- **Background Tasks:** Celery
- **Caching/Message Broker:** Redis
- **Database:** PostgreSQL

### Frontend
- **Templates:** Django Templates with HTMX
- **CSS Framework:** TailwindCSS
- **JavaScript:** Alpine.js (minimalist approach)

### Authentication & Authorization
- Django's built-in auth system (extended for custom roles)
- django-guardian (for object-level permissions)

### Monitoring & Analytics
- Matomo (open-source analytics, GDPR compliant)
- Sentry (error tracking)

### Deployment
- Docker & Docker Compose
- GitHub Actions (CI/CD)
- Nginx
- Let's Encrypt (SSL)

## Hosting & Scalability
- Self-hosted on VPS initially
- Designed for ~100 initial users with room to scale
- No paid third-party services initially

## User Roles & Permissions
- Mediap Support: Full system access for customer support
- Mediap Admin: System-wide configuration and user management
- Mediap Moderators: Content and user activity monitoring
- Mediap Editors: Content creation and management
- Service-specific roles:
  - Workflow Managers (cflows)
  - Process Designers (cflows)
  - Job Planners
  - Resource Managers
  - Team Leaders
  - Standard Users

## Compliance Requirements
- EU and GDPR standards compliance
- Proper data handling and user consent mechanisms
- Data portability and right to be forgotten implementation
- Privacy by design principles
- Clear data processing documentation
- Secure data storage with encryption

## Project Structure
```
mediap/
├── config/                  # Project settings
├── core/                    # Shared functionality
├── accounts/                # User management, profiles, roles
├── analytics/               # Usage tracking
├── licensing/               # License management
├── homepage/                # Marketing site, service listings
├── services/                # Mediap services
│   ├── cflows/              # Workflow management service
│   ├── job_planning/        # Job planning service
│   └── [other_services]/    # Future services
├── api/                     # API endpoints
├── frontend/                # Static assets
│   ├── css/
│   ├── js/
│   └── images/
└── docker/                  # Deployment configuration
```

## Key Features

### Core Platform
1. User authentication and role-based access control
2. Service discovery and integration
3. Unified dashboard
4. Analytics for user activity
5. Licensing management

### Service: CFlows
- Visual workflow designer
- Process templates and customization
- Automation rules and triggers
- Task assignment and notification system
- Approval chains
- Status tracking and reporting
- Integration with other Mediap services

### Service: Job Planning
- Project and job creation
- Resource allocation and management
- Task scheduling and deadline tracking
- Calendar views (daily, weekly, monthly)
- Workload balancing
- Progress tracking and reporting
- Time management tools
- Integration with CFlows for workflow-based jobs

## Development Workflow
- Single developer initially with plans to expand
- GitHub Actions for CI/CD pipeline:
  - Development environment for feature work
  - Testing environment for QA
  - Staging for pre-release verification
  - Production deployment with rollback capability

## Implementation Phases

### Phase 1: Foundation (Weeks 1-4)
- Project initialization with Docker setup
- Core authentication system with custom roles
- Database configuration and initial models
- Basic API structure
- Service framework integration

### Phase 2: Service Integration (Weeks 5-10)
- Migrate existing cflows functionality
- Migrate existing job planning functionality
- Unify UI/UX across services
- Implement cross-service communication

### Phase 3: Marketing & Licensing (Weeks 11-14)
- Develop homepage showcasing services
- Implement licensing system
- Create documentation
- Build admin dashboards for system management

### Phase 4: Analytics & Monitoring (Weeks 15-18)
- Implement GDPR-compliant analytics
- Set up monitoring and alerting
- Performance optimization
- Security auditing and hardening

## Notes
- All development should follow GDPR compliance guidelines
- Prioritize modular design to allow for future service additions
- Focus on maintainable code as the team will expand later
- Implement comprehensive logging for troubleshooting
- Design with API-first approach to enable future integrations
```
