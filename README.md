# openLMS - Laundry Management System

A comprehensive Django-based Laundry Management System designed for A&F Laundry Services with modern POS capabilities, customer management, and business analytics.

## 🚀 Features

- **Point of Sale (POS)**: Fast order processing with real-time pricing engine
- **Customer Management**: Complete customer profiles and service history
- **Service Management**: Flexible service types and pricing configuration
- **Order Tracking**: End-to-end order lifecycle management
- **Expense Management**: Business expense tracking with approval workflows
- **Business Reports**: Comprehensive analytics with export capabilities (PDF, Excel, CSV, JSON)
- **Role-Based Access**: Admin and staff user roles with granular permissions
- **Mobile-First Design**: Responsive UI optimized for tablets and mobile devices
- **Loyalty Program**: Customer loyalty points and rewards system

## 🛠 Technology Stack

- **Backend**: Django 4.x + Django REST Framework
- **Database**: SQLite (development) / PostgreSQL (production)
- **Frontend**: Django Templates + HTMX + Bootstrap 5
- **Authentication**: Django Auth + django-guardian
- **Deployment**: Docker + Nginx
- **Monitoring**: Built-in health checks and logging

## 📋 Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Git

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/asembereng/openLMS.git
   cd openLMS
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

6. **Start development server**
   ```bash
   python manage.py runserver
   ```

   Visit: http://127.0.0.1:8000

### Docker Deployment

1. **Quick Deploy**
   ```bash
   ./deploy.sh
   ```

2. **Manual Docker Commands**
   ```bash
   docker-compose -f docker-compose.production.yml up -d
   ```

## 🏗 Project Structure

```
openLMS/
├── accounts/          # User management and authentication
├── customers/         # Customer profiles and management
├── services/          # Service types and pricing
├── orders/           # POS operations and order tracking
├── expenses/         # Business expense management
├── reports/          # Analytics and reporting
├── system_settings/  # Application configuration
├── loyalty/          # Customer loyalty program
├── templates/        # Django templates
├── static/          # Static assets (CSS, JS, images)
└── docker/          # Container configuration
```

## 🎯 Core Modules

### Customer Management
- Customer profiles with contact information
- Service history and preferences
- Loyalty program integration
- SMS/WhatsApp notifications

### Service Management
- Configurable service types
- Flexible pricing models (per dozen, per piece)
- Service categories and descriptions
- Pricing history tracking

### Point of Sale (POS)
- Fast order entry interface
- Real-time price calculations
- Multiple payment methods
- Receipt generation and printing

### Order Management
- Order lifecycle tracking
- Status updates and notifications
- Delivery management
- Quality control workflows

### Business Analytics
- Revenue and profit reports
- Customer analytics
- Service performance metrics
- Export capabilities (PDF, Excel, CSV, JSON)

## 🔒 Security Features

- Role-based access control (RBAC)
- CSRF protection
- XSS protection headers
- Secure session management
- Input validation and sanitization
- SQL injection protection

## 🎨 User Interface

- **Modern Design**: Clean, professional interface
- **Mobile-First**: Responsive design for all devices
- **Fast Navigation**: HTMX-powered interactivity
- **Accessibility**: WCAG compliant design
- **Dark Mode**: Available for low-light environments

## 📊 Business Logic

### Pricing Engine
```python
unit_price = service_price_per_dozen / 12
total_amount = round(unit_price × quantity, 2)
```

### Currency Support
- Configurable currency symbols
- Multi-currency support ready
- Proper decimal handling
- Rounding strategies

## 🌍 Internationalization

- Timezone support (default: Africa/Lagos)
- Currency localization
- Date/time formatting
- Multi-language ready

## 📈 Performance

- Database query optimization
- Static file caching
- Image optimization
- Background task processing
- Connection pooling

## 🧪 Testing

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test accounts

# Coverage report
coverage run manage.py test
coverage report
```

## 📝 API Documentation

The system includes a RESTful API for mobile apps and integrations:

- **Authentication**: Token-based authentication
- **Endpoints**: Full CRUD operations for all modules
- **Documentation**: Auto-generated API docs
- **Rate Limiting**: Configurable rate limits

## 🔧 Configuration

### Environment Variables

Key environment variables in `.env`:

```bash
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///db.sqlite3
EMAIL_HOST=smtp.gmail.com
CURRENCY_SYMBOL=₦
TIME_ZONE=Africa/Lagos
```

### System Settings

Runtime configuration via database:
- Company information
- Email templates
- Pricing rules
- User preferences

## 🚀 Deployment

### Production Deployment

1. **Environment Setup**
   ```bash
   cp .env.example .env.production
   # Configure production settings
   ```

2. **Docker Deployment**
   ```bash
   ./deploy.sh
   ```

3. **Health Checks**
   - Application: `/health/`
   - Database connectivity
   - External service checks

### Monitoring

- Application logs: `./logs/django.log`
- Web server logs: `./logs/nginx.log`
- Error tracking: Sentry integration ready
- Performance monitoring: Built-in metrics

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write tests
5. Submit a pull request

## 📞 Support

- **Documentation**: See `/docs` directory
- **Issues**: GitHub Issues
- **Email**: admin@aflaundry.com

## 📄 License

Proprietary - A&F Laundry Services

---

**A&F Laundry Services** - Professional Laundry Management Solution