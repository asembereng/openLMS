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

7. **Access the application**
   - Main app: http://127.0.0.1:8000
   - Admin panel: http://127.0.0.1:8000/admin

### Docker Deployment (Production)

```bash
# Build and start with production configuration
docker-compose -f docker-compose.production.yml up -d --build

# Run migrations
docker-compose -f docker-compose.production.yml exec web python manage.py migrate

# Create superuser
docker-compose -f docker-compose.production.yml exec web python manage.py createsuperuser

# Access application at http://localhost
```

## 🏗 Architecture

```
openLMS/
├── accounts/          # User management & authentication
├── customers/         # Customer profiles & management
├── services/          # Service types & pricing
├── orders/           # POS & order management
├── expenses/         # Expense tracking & approval
├── reports/          # Business analytics & reporting
├── loyalty/          # Customer loyalty program
├── system_settings/  # System configuration
├── static/           # Frontend assets
├── templates/        # Django templates
└── docker/           # Docker configuration files
```

## 🔧 Configuration

### Environment Variables
Key configuration options in `.env`:

```bash
SECRET_KEY=your-secret-key
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
TIME_ZONE=Africa/Lagos
ALLOWED_HOSTS=localhost,127.0.0.1
```

### Business Configuration
- **Currency**: Configurable currency symbol and rounding
- **Pricing**: Per-dozen pricing with automatic unit calculation
- **Roles**: Admin (full access) and Staff (limited access)
- **Timezone**: Default UTC+1 (Africa/Lagos)

## 📊 Business Logic

### Pricing Engine
```python
unit_price = service_price_per_dozen / 12
total_amount = round(unit_price × pieces_count, 2)
```

### User Roles
- **Admin**: Full system access, user management, all reports
- **Staff**: Customer/order operations, limited reporting

## 🚀 Production Deployment

### Single Container with SQLite + Nginx

The project includes a production-ready Docker configuration that packages:
- Django application with Gunicorn
- SQLite database (included in container)
- Nginx web server
- Supervisor for process management

```bash
# Build production image
docker build -f Dockerfile.production -t openlms:latest .

# Run production container
docker run -d -p 80:80 --name openlms-prod openlms:latest
```

### Features
- **All-in-one container**: App, database, and web server
- **Persistent data**: SQLite database persists in container
- **Production ready**: Optimized for performance and security
- **Easy deployment**: Single container deployment

## 📈 Performance

- **Target**: <1s POS response time
- **Capacity**: 10k+ orders supported
- **Optimization**: Database query optimization with select_related
- **Caching**: Built-in Django caching framework

## 🧪 Testing

```bash
# Run all tests
python manage.py test

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

## 📝 API Documentation

Interactive API documentation available at:
- **Swagger UI**: `/api/docs/`
- **ReDoc**: `/api/redoc/`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue on GitHub
- Email: support@africanflex.com

## 🙏 Acknowledgments

- Built for A&F Laundry Services
- Powered by Django and SQLite/PostgreSQL
- UI components from Bootstrap 5
- Interactive features with HTMX