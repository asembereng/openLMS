#!/bin/bash

# A&F Laundry Management System - Production Deployment Script
# Version: 1.0.0
# Date: December 19, 2024

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="openLMS"
REPO_URL="https://github.com/asembereng/openLMS.git"
APP_DIR="/opt/openlms"
DOCKER_COMPOSE_FILE="docker-compose.production.yml"
BACKUP_DIR="/opt/backups/openlms"
LOG_FILE="/var/log/openlms-deploy.log"

# Functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" | tee -a "$LOG_FILE"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}" | tee -a "$LOG_FILE"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root for security reasons"
    fi
}

# Check system requirements
check_requirements() {
    info "Checking system requirements..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
    fi
    
    # Check Git
    if ! command -v git &> /dev/null; then
        error "Git is not installed. Please install Git first."
    fi
    
    # Check available disk space (minimum 5GB)
    available_space=$(df / | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt 5242880 ]; then  # 5GB in KB
        warning "Low disk space. Minimum 5GB recommended."
    fi
    
    log "System requirements check completed"
}

# Create necessary directories
setup_directories() {
    info "Setting up directories..."
    
    sudo mkdir -p "$APP_DIR"
    sudo mkdir -p "$BACKUP_DIR"
    sudo mkdir -p "$(dirname "$LOG_FILE")"
    
    # Set ownership
    sudo chown -R "$USER":"$USER" "$APP_DIR"
    sudo chown -R "$USER":"$USER" "$BACKUP_DIR"
    
    log "Directories created successfully"
}

# Clone or update repository
setup_repository() {
    info "Setting up repository..."
    
    if [ -d "$APP_DIR/.git" ]; then
        log "Repository exists, pulling latest changes..."
        cd "$APP_DIR"
        git fetch origin
        git checkout main
        git pull origin main
    else
        log "Cloning repository..."
        git clone "$REPO_URL" "$APP_DIR"
        cd "$APP_DIR"
    fi
    
    # Checkout specific version tag if provided
    if [ "${DEPLOY_VERSION:-}" ]; then
        log "Checking out version $DEPLOY_VERSION"
        git checkout "$DEPLOY_VERSION"
    fi
    
    log "Repository setup completed"
}

# Setup environment configuration
setup_environment() {
    info "Setting up environment configuration..."
    
    cd "$APP_DIR"
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log "Created .env from .env.example"
        else
            log "Creating basic .env file"
            cat > .env << EOF
# Production Configuration
SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,$(hostname -I | awk '{print $1}')

# Database
DATABASE_URL=sqlite:///data/db.sqlite3

# Email (Configure with your SMTP settings)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# Security
SECURE_SSL_REDIRECT=False
SECURE_HSTS_SECONDS=0

# Time Zone
TIME_ZONE=Africa/Lagos

# Currency
CURRENCY_SYMBOL=₦
EOF
        fi
        
        warning "Please edit .env file with your production settings"
        warning "Especially configure EMAIL settings and SECRET_KEY"
    else
        log "Environment file already exists"
    fi
}

# Backup existing data
backup_data() {
    info "Creating backup of existing data..."
    
    cd "$APP_DIR"
    timestamp=$(date +%Y%m%d_%H%M%S)
    backup_file="$BACKUP_DIR/backup_$timestamp.tar.gz"
    
    if [ -f "data/db.sqlite3" ]; then
        tar -czf "$backup_file" data/ media/ logs/ 2>/dev/null || true
        log "Backup created: $backup_file"
    else
        log "No existing data to backup"
    fi
}

# Build and deploy with Docker
deploy_application() {
    info "Deploying application with Docker..."
    
    cd "$APP_DIR"
    
    # Stop existing containers
    if [ -f "$DOCKER_COMPOSE_FILE" ]; then
        docker-compose -f "$DOCKER_COMPOSE_FILE" down || true
    fi
    
    # Build and start new containers
    docker-compose -f "$DOCKER_COMPOSE_FILE" build
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
    
    # Wait for services to start
    sleep 30
    
    log "Application deployed successfully"
}

# Initialize database and system
initialize_system() {
    info "Initializing system..."
    
    cd "$APP_DIR"
    
    # Run migrations
    docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T web python manage.py migrate
    
    # Create directories
    docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T web python manage.py collectstatic --noinput
    
    # Initialize system settings
    docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T web python manage.py init_system_settings
    
    log "System initialization completed"
}

# Health check
health_check() {
    info "Running health check..."
    
    cd "$APP_DIR"
    max_attempts=30
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s http://localhost:8000/health/ > /dev/null 2>&1; then
            log "Health check passed - Application is running"
            return 0
        fi
        
        info "Health check attempt $attempt/$max_attempts - Waiting..."
        sleep 5
        ((attempt++))
    done
    
    error "Health check failed - Application may not be running properly"
}

# Display status and next steps
show_status() {
    info "Deployment Status:"
    
    cd "$APP_DIR"
    docker-compose -f "$DOCKER_COMPOSE_FILE" ps
    
    echo ""
    log "🎉 Deployment completed successfully!"
    echo ""
    info "Next steps:"
    echo "1. Configure your web server (Nginx) to proxy to port 8000"
    echo "2. Set up SSL certificates for production"
    echo "3. Create admin user: docker-compose -f $DOCKER_COMPOSE_FILE exec web python manage.py createsuperuser"
    echo "4. Configure email settings in .env file"
    echo "5. Set up regular backups"
    echo ""
    info "Application URLs:"
    echo "- Main Application: http://$(hostname -I | awk '{print $1}'):8000/"
    echo "- Admin Panel: http://$(hostname -I | awk '{print $1}'):8000/admin/"
    echo "- API Documentation: http://$(hostname -I | awk '{print $1}'):8000/api/docs/"
    echo "- Health Check: http://$(hostname -I | awk '{print $1}'):8000/health/"
    echo ""
    info "Log locations:"
    echo "- Deployment log: $LOG_FILE"
    echo "- Application logs: $APP_DIR/logs/"
    echo "- Docker logs: docker-compose -f $DOCKER_COMPOSE_FILE logs"
}

# Main deployment function
main() {
    log "Starting openLMS production deployment..."
    
    check_root
    check_requirements
    setup_directories
    setup_repository
    setup_environment
    backup_data
    deploy_application
    initialize_system
    health_check
    show_status
    
    log "Deployment completed successfully! 🚀"
}

# Script options
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "update")
        setup_repository
        backup_data
        deploy_application
        health_check
        show_status
        ;;
    "backup")
        backup_data
        ;;
    "health")
        health_check
        ;;
    "logs")
        cd "$APP_DIR"
        docker-compose -f "$DOCKER_COMPOSE_FILE" logs -f
        ;;
    "stop")
        cd "$APP_DIR"
        docker-compose -f "$DOCKER_COMPOSE_FILE" down
        ;;
    "start")
        cd "$APP_DIR"
        docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
        ;;
    "restart")
        cd "$APP_DIR"
        docker-compose -f "$DOCKER_COMPOSE_FILE" restart
        ;;
    *)
        echo "Usage: $0 {deploy|update|backup|health|logs|stop|start|restart}"
        echo ""
        echo "Commands:"
        echo "  deploy  - Full deployment (default)"
        echo "  update  - Update to latest version"
        echo "  backup  - Create data backup"
        echo "  health  - Run health check"
        echo "  logs    - Show application logs"
        echo "  stop    - Stop application"
        echo "  start   - Start application"
        echo "  restart - Restart application"
        exit 1
        ;;
esac
