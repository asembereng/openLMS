# Copilot Instructions for Laundry Management System

<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

## Project Overview
This is a Django-based Laundry Management System (LMS) for A&F Laundry Services with the following key characteristics:

### Technology Stack
- **Backend**: Django 4.x with Django REST Framework
- **Database**: PostgreSQL 15+
- **Frontend**: Django templates with HTMX for interactivity
- **Authentication**: Django Auth + django-guardian for role-based permissions
- **Deployment**: Docker Compose with Gunicorn and Nginx

### Architecture
- **Apps Structure**:
  - `accounts` - User management and authentication
  - `customers` - Customer management
  - `services` - Service types and pricing
  - `orders` - POS operations and order management
  - `expenses` - Expense tracking
  - `reports` - Business reporting and analytics

### User Roles
- **Admin**: Full system access, pricing configuration, user management, all reports
- **Normal User**: Customer/order operations, expense entry, limited reporting

### Key Business Rules
1. **Pricing Engine**: `unit_price = service_price_per_dozen / 12`, `total = round(unit_price × pieces, 2)`
2. **Currency**: Support configurable currency symbols and rounding rules
3. **Timezone**: Default Africa/Lagos (UTC+1), store all datetimes as UTC
4. **Audit Trail**: Log all CRUD operations with user and timestamp
5. **Data Preservation**: Use CASCADE=PROTECT to preserve historical data

### Development Guidelines
- Follow Django best practices and PEP 8
- Use class-based views with mixins for DRY code
- Implement comprehensive test coverage (target: 80%+)
- Use Django's built-in security features (CSRF, XSS protection)
- Design mobile-first responsive UI
- Implement proper error handling and logging
- Use environment variables for configuration (12-factor app)

### Security Requirements
- Enforce HTTPS in production
- Implement proper RBAC with django-guardian
- Use Django's built-in protection against common vulnerabilities
- Validate all user inputs
- Implement proper session management

### Performance Targets
- POS operations should respond in <1 second
- Support up to 10k orders without performance degradation
- Optimize database queries with select_related/prefetch_related

When generating code, prioritize:
1. Security and data integrity
2. Code maintainability and readability
3. Performance optimization
4. Mobile-responsive design
5. Comprehensive error handling
