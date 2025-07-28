# openLMS Production Deployment

This directory contains everything needed to deploy the openLMS application in a single Docker container with Django, SQLite database, and Nginx web server.

## Quick Start

1. **Deploy the application:**
   ```bash
   ./deploy.sh
   ```

2. **Access the application:**
   - URL: http://localhost
   - Admin login: admin@openlms.com / admin123

## What's Included

### Container Architecture
- **Django Application**: Running with Gunicorn WSGI server
- **SQLite Database**: Lightweight, file-based database
- **Nginx Web Server**: Serves static files and proxies to Django
- **Supervisor**: Process manager for Django and Nginx

### Files Structure
```
docker/
├── nginx.conf         # Nginx configuration
├── supervisord.conf   # Supervisor configuration
└── setup.sh          # Django initialization script

Dockerfile.production     # Production container definition
docker-compose.production.yml  # Container orchestration
deploy.sh             # Deployment automation script
```

## Deployment Commands

### Basic Operations
```bash
# Deploy application
./deploy.sh

# Stop application
./deploy.sh --stop

# Restart application
./deploy.sh --restart

# View logs
./deploy.sh --logs

# Check status
./deploy.sh --status

# Create backup
./deploy.sh --backup
```

### Manual Docker Commands
```bash
# Build container
docker-compose -f docker-compose.production.yml build

# Start services
docker-compose -f docker-compose.production.yml up -d

# View logs
docker-compose -f docker-compose.production.yml logs -f

# Access container shell
docker-compose -f docker-compose.production.yml exec openlms bash

# Stop services
docker-compose -f docker-compose.production.yml down
```

## Data Persistence

### Volumes
- `./data/` - Application data (database, media files)
- `./logs/` - Application and web server logs

### Backup Strategy
```bash
# Create backup
./deploy.sh --backup

# Restore from backup (manual)
tar -xzf openlms_backup_YYYYMMDD_HHMMSS.tar.gz
```

## Configuration

### Environment Variables
Set these in your environment or `.env` file:

```bash
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=your-domain.com,localhost
```

### Production Settings
Located in `laundry_management/settings_production.py`:
- SQLite database configuration
- Security headers and settings
- Static file handling with WhiteNoise
- Logging configuration

## Security Features

### Container Security
- Non-root user for Django processes
- Security headers in Nginx
- File permission restrictions
- Health check monitoring

### Application Security
- CSRF protection enabled
- XSS protection headers
- Secure cookie settings
- SQL injection protection via Django ORM

## Monitoring

### Health Checks
- Container health check at `/health/`
- Automatic restart on failure
- Process supervision with Supervisor

### Logs
```bash
# View all logs
./deploy.sh --logs

# View specific service logs
docker-compose -f docker-compose.production.yml logs django
docker-compose -f docker-compose.production.yml logs nginx
```

## Troubleshooting

### Common Issues

1. **Port 80 already in use:**
   ```bash
   # Check what's using port 80
   sudo lsof -i :80
   
   # Stop the service or change port in docker-compose.production.yml
   ```

2. **Permission denied errors:**
   ```bash
   # Fix data directory permissions
   sudo chown -R $USER:$USER ./data
   chmod -R 755 ./data
   ```

3. **Container won't start:**
   ```bash
   # Check container logs
   docker-compose -f docker-compose.production.yml logs
   
   # Rebuild container
   docker-compose -f docker-compose.production.yml build --no-cache
   ```

### Database Issues
```bash
# Access Django shell
docker-compose -f docker-compose.production.yml exec openlms python manage.py shell

# Run migrations manually
docker-compose -f docker-compose.production.yml exec openlms python manage.py migrate

# Create superuser
docker-compose -f docker-compose.production.yml exec openlms python manage.py createsuperuser
```

## Performance Tuning

### Gunicorn Workers
Adjust workers in `docker/supervisord.conf`:
```ini
command=gunicorn ... --workers 4  # Increase for more traffic
```

### Nginx Caching
Static files are cached for 1 year by default. Adjust in `docker/nginx.conf`:
```nginx
location /static/ {
    expires 1y;  # Adjust cache duration
}
```

## Scaling Considerations

### Single Container Limitations
- SQLite has write concurrency limitations
- No horizontal scaling capability
- All services in one container (single point of failure)

### Migration Path
For production scale, consider:
1. Separate containers for Django and Nginx
2. External PostgreSQL database
3. Redis for caching and sessions
4. Load balancer for multiple Django instances

## Support

For issues and questions:
1. Check the logs: `./deploy.sh --logs`
2. Verify container status: `./deploy.sh --status`
3. Review Django admin at http://localhost/admin/
4. Access container shell for debugging

## Version Information
- Django: 4.x
- Python: 3.11
- Nginx: Latest stable
- SQLite: Built-in with Python
