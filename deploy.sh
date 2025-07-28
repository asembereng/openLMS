#!/bin/bash

# openLMS Production Deployment Script
# This script sets up and deploys the openLMS application in a Docker container

set -e

echo "🚀 Starting openLMS Production Deployment"
echo "========================================"

# Configuration
COMPOSE_FILE="docker-compose.production.yml"
SERVICE_NAME="openlms"
DATA_DIR="./data"
LOGS_DIR="./logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker and Docker Compose are installed
check_dependencies() {
    print_status "Checking dependencies..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_success "Dependencies check passed"
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    mkdir -p "$DATA_DIR"
    mkdir -p "$DATA_DIR/media"
    mkdir -p "$DATA_DIR/db"
    mkdir -p "$LOGS_DIR"
    
    print_success "Directories created"
}

# Generate secret key if not provided
generate_secret_key() {
    if [ -z "$DJANGO_SECRET_KEY" ]; then
        print_status "Generating Django secret key..."
        export DJANGO_SECRET_KEY=$(python3 -c "
import secrets
import string
alphabet = string.ascii_letters + string.digits + '!@#$%^&*(-_=+)'
print(''.join(secrets.choice(alphabet) for i in range(50)))
")
        print_success "Secret key generated"
    fi
}

# Set proper permissions
set_permissions() {
    print_status "Setting proper permissions..."
    
    # Make sure the data directory is writable
    chmod -R 755 "$DATA_DIR"
    chmod -R 755 "$LOGS_DIR"
    
    print_success "Permissions set"
}

# Build and start the container
deploy_container() {
    print_status "Building and starting the container..."
    
    # Stop any existing containers
    docker-compose -f "$COMPOSE_FILE" down || true
    
    # Build the container
    docker-compose -f "$COMPOSE_FILE" build --no-cache
    
    # Start the container
    docker-compose -f "$COMPOSE_FILE" up -d
    
    print_success "Container deployed"
}

# Wait for the application to be ready
wait_for_app() {
    print_status "Waiting for application to be ready..."
    
    max_attempts=30
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost/health/ &> /dev/null; then
            print_success "Application is ready!"
            return 0
        fi
        
        print_status "Attempt $attempt/$max_attempts - waiting for application..."
        sleep 10
        ((attempt++))
    done
    
    print_error "Application failed to start within expected time"
    return 1
}

# Show deployment information
show_deployment_info() {
    echo ""
    echo "🎉 Deployment Complete!"
    echo "======================"
    echo ""
    echo "Application URL: http://localhost"
    echo "Admin Login: admin@openlms.com / admin123"
    echo ""
    echo "Useful Commands:"
    echo "  View logs:     docker-compose -f $COMPOSE_FILE logs -f"
    echo "  Stop app:      docker-compose -f $COMPOSE_FILE down"
    echo "  Restart app:   docker-compose -f $COMPOSE_FILE restart"
    echo "  Shell access:  docker-compose -f $COMPOSE_FILE exec $SERVICE_NAME bash"
    echo ""
    echo "Data Directories:"
    echo "  Database:      $DATA_DIR/db/"
    echo "  Media files:   $DATA_DIR/media/"
    echo "  Logs:          $LOGS_DIR/"
    echo ""
}

# Show usage information
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --help, -h      Show this help message"
    echo "  --stop          Stop the application"
    echo "  --restart       Restart the application"
    echo "  --logs          Show application logs"
    echo "  --status        Show container status"
    echo "  --backup        Create a backup of the data"
    echo ""
}

# Handle command line arguments
case "${1:-deploy}" in
    --help|-h)
        show_usage
        exit 0
        ;;
    --stop)
        print_status "Stopping openLMS..."
        docker-compose -f "$COMPOSE_FILE" down
        print_success "openLMS stopped"
        exit 0
        ;;
    --restart)
        print_status "Restarting openLMS..."
        docker-compose -f "$COMPOSE_FILE" restart
        print_success "openLMS restarted"
        exit 0
        ;;
    --logs)
        docker-compose -f "$COMPOSE_FILE" logs -f
        exit 0
        ;;
    --status)
        docker-compose -f "$COMPOSE_FILE" ps
        exit 0
        ;;
    --backup)
        BACKUP_FILE="openlms_backup_$(date +%Y%m%d_%H%M%S).tar.gz"
        print_status "Creating backup: $BACKUP_FILE"
        tar -czf "$BACKUP_FILE" "$DATA_DIR"
        print_success "Backup created: $BACKUP_FILE"
        exit 0
        ;;
    deploy)
        # Main deployment process
        check_dependencies
        create_directories
        generate_secret_key
        set_permissions
        deploy_container
        wait_for_app
        show_deployment_info
        ;;
    *)
        print_error "Unknown option: $1"
        show_usage
        exit 1
        ;;
esac
