# MetaTask Platform

**Version:** 2.0  
**Last Updated:** December 2024  
**Owner:** @LiamOlsson

## Overview

MetaTask is a comprehensive multi-tenant business process management platform that integrates workflow management, team collaboration, and resource scheduling. Built with Django and modern web technologies, it provides organizations with powerful tools to streamline their operations while maintaining complete data isolation and security.

## 🚀 Current Features

### Core Platform
- **Multi-tenant Architecture**: Complete organization isolation with personal and business workspace types
- **User Management**: Extended user profiles with role-based access control
- **Licensing System**: Tiered licensing with usage tracking and automatic enforcement
- **Modern UI/UX**: TailwindCSS-based responsive design with Alpine.js interactivity

### Authentication & Registration
- **Streamlined Registration Flow**: Account type selection as first step (Personal vs Business)
- **Personal Accounts**: Single-step registration with automatic workspace creation
- **Business Accounts**: Multi-step process with organization setup and team invitations
- **GDPR Compliance**: Privacy policy and terms acceptance tracking

### Organization Management  
- **Personal Organizations**: Single-user workspaces with free tier access
- **Business Organizations**: Multi-user collaboration with advanced features
- **Team Management**: Flexible team structures with capacity planning
- **Access Control**: Organization-scoped permissions and feature gating

## 📋 Services

### CFlows - Workflow Management System
**Status**: ✅ Fully Implemented

**Core Features:**
- **Flexible Workflow Engine**: Step-based process definitions with custom transitions
- **Work Item Tracking**: Full lifecycle management with history and audit trails
- **Team Booking**: Resource scheduling and capacity management
- **Calendar Integration**: FullCalendar with team bookings and events
- **Real-time Notifications**: WebSocket-powered instant updates
- **Project Management**: Hierarchical project organization with member roles
- **Transition Customization**: Visual customization (colors, icons) and behavioral controls
- **Field Customization**: Show/hide/require standard fields, custom field integration
- **Admin Interface**: Organization-scoped administration panel

**Business Use Cases:**
- Service delivery workflows
- Quality assurance processes
- Dealership vehicle processing
- Professional services management
- Manufacturing workflow control

### Job Planning Service
**Status**: 🚧 Coming Soon
- Resource allocation and scheduling
- Project management capabilities  
- Calendar integration
- Progress tracking and analytics

## 🏗️ Technical Architecture

### Backend Stack
- **Framework**: Django 5.x with Python 3.12+
- **Database**: PostgreSQL (SQLite for development)
- **Caching**: Redis for sessions and WebSocket channels
- **Real-time**: Django Channels with WebSocket support
- **Task Queue**: Celery for background processing

### Frontend Stack
- **Templates**: Django Templates with HTMX
- **CSS**: TailwindCSS for responsive design
- **JavaScript**: Alpine.js for interactivity
- **Calendar**: FullCalendar integration
- **Icons**: Font Awesome

### Deployment
- **Containerization**: Docker with Docker Compose
- **Reverse Proxy**: Traefik with automatic HTTPS
- **Static Files**: Optimized asset serving
- **Environment**: Secure configuration management

## 💰 Licensing Tiers

### Personal Free
- 1 user
- 3 workflows
- 100 work items
- 2 projects
- 1GB storage

### Basic Team - $29/month
- 10 users
- 25 workflows
- 1,000 work items
- 50 projects
- 10GB storage

### Professional - $79/month  
- 50 users
- 100 workflows
- 10,000 work items
- 200 projects
- 100GB storage

### Enterprise - $299/month
- Unlimited users
- Unlimited workflows
- Unlimited work items
- Unlimited projects
- 1TB storage

## 🚀 Quick Start

### Development Setup
```bash
# Clone the repository
git clone <repository-url>
cd mediap

# Start with Docker Compose
docker-compose up -d

# Create sample data
docker-compose exec web python manage.py create_cflows_sample_data

# Access the application
open http://localhost:8000
```

### Demo Access
- **URL**: `http://localhost:8000`
- **Admin**: `admin / admin123`
- **Sample Organization**: Demo Car Dealership
- **Sample Workflows**: Car sales process with multiple teams

## 📊 Key URLs

### Public Pages
- `/` - Homepage with service overview
- `/about/` - About page
- `/services/` - Service listings
- `/contact/` - Contact information

### Authentication
- `/accounts/register/` - Account type selection (start here)
- `/accounts/register/personal/` - Personal account registration
- `/accounts/register/business/` - Business account registration
- `/accounts/login/` - User login
- `/accounts/profile/` - User dashboard

### Services
- `/services/cflows/` - CFlows dashboard and workflow management
- `/services/job-planning/` - Job Planning (coming soon)

### Administration
- `/admin/` - Django admin (platform level)
- `/admin/core/` - Organization and user management
- `/admin/licensing/` - License management and usage monitoring

## 🛡️ Security & Compliance

### Data Protection
- **Multi-tenant Isolation**: Complete data separation between organizations
- **CSRF Protection**: Cross-site request forgery prevention
- **Rate Limiting**: Protection against abuse
- **Secure Authentication**: Password hashing and session management

### GDPR Compliance
- **Privacy by Design**: Built-in privacy protection
- **Data Portability**: Export capabilities
- **Right to be Forgotten**: Data deletion support
- **Consent Management**: Privacy policy and terms tracking

## 📈 Monitoring & Analytics

### Usage Tracking
- **License Monitoring**: Real-time usage against limits
- **Organization Analytics**: Workspace activity tracking
- **Performance Metrics**: System health monitoring
- **Audit Trails**: Complete activity logging

### Development Tools
- **Comprehensive Testing**: Test coverage across components
- **Developer Documentation**: Setup and contribution guides
- **Management Commands**: Automated workflow and data management

## 🔮 Roadmap

### Immediate (Q1 2025)
- **Email Integration**: SMTP configuration for notifications
- **Password Reset**: Forgotten password functionality
- **Profile Management**: User information editing
- **File Uploads**: Profile pictures and document attachments

### Short-term (Q2 2025)
- **Job Planning Service**: Complete implementation
- **Mobile App**: React Native companion app
- **API Development**: RESTful API with authentication
- **Advanced Analytics**: Usage dashboards and insights

### Long-term (Q3-Q4 2025)
- **Third-party Integrations**: CRM, calendar, and SSO
- **Advanced Automation**: Workflow triggers and rules
- **Enterprise Features**: Advanced security and compliance
- **Multi-language Support**: Internationalization

## 🤝 Contributing

### Development Environment
1. **Docker Required**: All services containerized
2. **Python 3.12+**: Modern Python features
3. **Node.js**: For frontend asset processing
4. **Git Flow**: Feature branches and pull requests

### Code Standards
- **Django Best Practices**: Follow Django conventions
- **PEP 8**: Python code style
- **Type Hints**: Use type annotations
- **Testing**: Write tests for new features

## 📞 Support & Contact

- **Documentation**: [Internal wiki or docs site]
- **Issues**: GitHub Issues for bug reports
- **Discussions**: GitHub Discussions for questions
- **Contact**: [support email]

## 📄 License

[License type - e.g., MIT, proprietary, etc.]

---

**MetaTask Platform** - Streamlining workflows, empowering organizations.