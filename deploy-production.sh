#!/bin/bash

# A&F Laundry Management System - Production Deployment Script
# Version: 1.0.0
# Date: August 5, 2025
# Hostname: af.proxysolutions.io

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
HOSTNAME="af.proxysolutions.io"

# Create logs directory in project folder instead of /var/log
LOGS_DIR="./logs"
mkdir -p "$LOGS_DIR"
LOG_FILE="$LOGS_DIR/deploy.log"

# Ensure log file is writable
touch "$LOG_FILE" 2>/dev/null || {
    echo "Warning: Cannot create log file at $LOG_FILE, continuing without logging..."
    LOG_FILE="/dev/null"
}

# Functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE" 2>/dev/null || echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" | tee -a "$LOG_FILE" 2>/dev/null || echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}" | tee -a "$LOG_FILE" 2>/dev/null || echo -e "${YELLOW}[WARNING] $1${NC}"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}" | tee -a "$LOG_FILE" 2>/dev/null || echo -e "${BLUE}[INFO] $1${NC}"
}

# Prompt user for installation
prompt_install() {
    local package_name="$1"
    local install_command="$2"
    
    echo -e "${YELLOW}[PROMPT] $package_name is not installed.${NC}"
    read -p "Would you like to install $package_name now? (y/n): " -n 1 -r
    echo    # Move to a new line
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        info "Installing $package_name..."
        if eval "$install_command"; then
            log "$package_name installed successfully"
            return 0
        else
            error "Failed to install $package_name"
        fi
    else
        warning "Skipping $package_name installation"
        return 1
    fi
}

# Detect operating system
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v apt-get &> /dev/null; then
            echo "ubuntu"
        elif command -v yum &> /dev/null; then
            echo "centos"
        elif command -v dnf &> /dev/null; then
            echo "fedora"
        else
            echo "linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    else
        echo "unknown"
    fi
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root for security reasons. Please run as a regular user. The script will use sudo when needed."
    fi
}

# Print deployment banner
print_banner() {
    echo ""
    echo "🚀 A&F Laundry Management System - Production Deployment"
    echo "========================================================="
    echo "📅 Date: $(date)"
    echo "🌐 Target: $HOSTNAME"
    echo "📁 Project: openLMS"
    echo "📝 Log file: $LOG_FILE"
    echo ""
}

# Check system requirements
check_requirements() {
    info "Checking system requirements..."
    
    local missing_requirements=()
    local os_type=$(detect_os)
    
    info "Detected OS: $os_type"
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        info "Docker is not installed."
        case $os_type in
            "ubuntu")
                install_cmd="curl -fsSL https://get.docker.com | sh && sudo usermod -aG docker \$USER && newgrp docker"
                ;;
            "centos"|"fedora")
                install_cmd="curl -fsSL https://get.docker.com | sh && sudo usermod -aG docker \$USER && sudo systemctl enable docker && sudo systemctl start docker"
                ;;
            "macos")
                install_cmd="echo 'Please install Docker Desktop for Mac from https://www.docker.com/products/docker-desktop'"
                ;;
            *)
                install_cmd="curl -fsSL https://get.docker.com | sh && sudo usermod -aG docker \$USER"
                ;;
        esac
        
        if prompt_install "Docker" "$install_cmd"; then
            info "Docker installed. You may need to log out and back in for group changes to take effect."
        else
            missing_requirements+=("Docker")
        fi
    else
        log "Docker is installed"
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        info "Docker Compose is not installed."
        case $os_type in
            "ubuntu"|"centos"|"fedora"|"linux")
                install_cmd="sudo curl -L \"https://github.com/docker/compose/releases/latest/download/docker-compose-\$(uname -s)-\$(uname -m)\" -o /usr/local/bin/docker-compose && sudo chmod +x /usr/local/bin/docker-compose"
                ;;
            "macos")
                install_cmd="brew install docker-compose || echo 'Please install Docker Compose manually or via Docker Desktop'"
                ;;
            *)
                install_cmd="echo 'Please install Docker Compose manually for your OS'"
                ;;
        esac
        
        if prompt_install "Docker Compose" "$install_cmd"; then
            log "Docker Compose installed successfully"
        else
            missing_requirements+=("Docker Compose")
        fi
    else
        log "Docker Compose is installed"
    fi
    
    # Check Git
    if ! command -v git &> /dev/null; then
        info "Git is not installed."
        case $os_type in
            "ubuntu")
                install_cmd="sudo apt-get update && sudo apt-get install -y git"
                ;;
            "centos")
                install_cmd="sudo yum install -y git"
                ;;
            "fedora")
                install_cmd="sudo dnf install -y git"
                ;;
            "macos")
                install_cmd="brew install git || xcode-select --install"
                ;;
            *)
                install_cmd="echo 'Please install Git manually for your OS'"
                ;;
        esac
        
        if prompt_install "Git" "$install_cmd"; then
            log "Git installed successfully"
        else
            missing_requirements+=("Git")
        fi
    else
        log "Git is installed"
    fi
    
    # Check curl
    if ! command -v curl &> /dev/null; then
        info "curl is not installed."
        case $os_type in
            "ubuntu")
                install_cmd="sudo apt-get update && sudo apt-get install -y curl"
                ;;
            "centos")
                install_cmd="sudo yum install -y curl"
                ;;
            "fedora")
                install_cmd="sudo dnf install -y curl"
                ;;
            "macos")
                install_cmd="brew install curl"
                ;;
            *)
                install_cmd="echo 'Please install curl manually for your OS'"
                ;;
        esac
        
        if prompt_install "curl" "$install_cmd"; then
            log "curl installed successfully"
        else
            missing_requirements+=("curl")
        fi
    else
        log "curl is installed"
    fi
    
    # Check Python3 (needed for Django secret key generation)
    if ! command -v python3 &> /dev/null; then
        info "Python3 is not installed."
        case $os_type in
            "ubuntu")
                install_cmd="sudo apt-get update && sudo apt-get install -y python3 python3-pip"
                ;;
            "centos")
                install_cmd="sudo yum install -y python3 python3-pip"
                ;;
            "fedora")
                install_cmd="sudo dnf install -y python3 python3-pip"
                ;;
            "macos")
                install_cmd="brew install python3"
                ;;
            *)
                install_cmd="echo 'Please install Python3 manually for your OS'"
                ;;
        esac
        
        if prompt_install "Python3" "$install_cmd"; then
            log "Python3 installed successfully"
        else
            missing_requirements+=("Python3")
        fi
    else
        log "Python3 is installed"
    fi
    
    # Check available disk space (minimum 5GB)
    available_space=$(df / | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt 5242880 ]; then  # 5GB in KB
        warning "Low disk space. Available: $(($available_space / 1024 / 1024))GB. Minimum 5GB recommended."
    else
        log "Sufficient disk space available: $(($available_space / 1024 / 1024))GB"
    fi
    
    # Check if any critical requirements are missing
    if [ ${#missing_requirements[@]} -gt 0 ]; then
        echo ""
        error "Critical requirements missing: ${missing_requirements[*]}"
        echo ""
        info "Manual installation instructions:"
        
        for req in "${missing_requirements[@]}"; do
            case $req in
                "Docker")
                    echo "• Docker: Visit https://docs.docker.com/get-docker/ for installation instructions"
                    ;;
                "Docker Compose")
                    echo "• Docker Compose: Visit https://docs.docker.com/compose/install/ for installation instructions"
                    ;;
                "Git")
                    echo "• Git: Visit https://git-scm.com/downloads for installation instructions"
                    ;;
                "curl")
                    echo "• curl: Usually available in most package managers (apt, yum, dnf, brew)"
                    ;;
                "Python3")
                    echo "• Python3: Visit https://www.python.org/downloads/ for installation instructions"
                    ;;
            esac
        done
        
        echo ""
        echo "After installing the missing requirements, run this script again."
        exit 1
    fi
    
    log "System requirements check completed successfully"
}

# Create necessary directories
setup_directories() {
    info "Setting up directories..."
    
    # Create project directories in current working directory if running locally
    if [ "$(pwd)" != "$APP_DIR" ]; then
        mkdir -p data/{db,media,backups} logs staticfiles
        chmod 755 data logs staticfiles 2>/dev/null || true
        chmod 755 data/{db,media,backups} 2>/dev/null || true
        log "Local project directories created"
    fi
    
    # Create production directories (requires sudo)
    sudo mkdir -p "$APP_DIR"
    sudo mkdir -p "$BACKUP_DIR"
    
    # Set ownership
    sudo chown -R "$USER":"$USER" "$APP_DIR"
    sudo chown -R "$USER":"$USER" "$BACKUP_DIR"
    
    log "Production directories created successfully"
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
ALLOWED_HOSTS=$HOSTNAME,localhost,127.0.0.1,$(hostname -I | awk '{print $1}' 2>/dev/null || echo "")

# Database
DATABASE_URL=sqlite:///data/db.sqlite3

# Email (Configure with your SMTP settings)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=noreply@$HOSTNAME

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
    
    # Create required directories for bind mounts
    mkdir -p data logs staticfiles media
    chmod 755 data logs staticfiles media 2>/dev/null || true
    
    # Stop existing containers
    if [ -f "$DOCKER_COMPOSE_FILE" ]; then
        docker-compose -f "$DOCKER_COMPOSE_FILE" down || true
    fi
    
    # Clean up conflicting volumes if they exist
    info "Cleaning up any conflicting Docker volumes..."
    docker volume rm openlms_openlms_data openlms_openlms_logs 2>/dev/null || true
    docker volume rm openlms_data openlms_logs 2>/dev/null || true
    
    # Remove any containers with the old naming
    docker rm -f openlms_openlms_1 openlms_web_1 2>/dev/null || true
    
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
    
    # Try multiple URLs for health check
    health_urls=(
        "http://localhost/health/"
        "http://127.0.0.1/health/"
        "http://$HOSTNAME/health/"
    )
    
    while [ $attempt -le $max_attempts ]; do
        for url in "${health_urls[@]}"; do
            if curl -f -s --connect-timeout 5 --max-time 10 "$url" > /dev/null 2>&1; then
                log "Health check passed - Application is running at $url"
                return 0
            fi
        done
        
        info "Health check attempt $attempt/$max_attempts - Waiting..."
        sleep 5
        ((attempt++))
    done
    
    error "Health check failed - Application may not be running properly. Check logs with: docker-compose -f $DOCKER_COMPOSE_FILE logs"
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
    echo "1. Set up SSL certificates for production: certbot --nginx -d $HOSTNAME"
    echo "2. Create admin user: docker-compose -f $DOCKER_COMPOSE_FILE exec web python manage.py createsuperuser"
    echo "3. Configure email settings in .env file"
    echo "4. Set up regular backups with: ./deploy-production.sh backup"
    echo "5. Monitor logs with: ./deploy-production.sh logs"
    echo ""
    info "Application URLs:"
    echo "- Main Application: http://$HOSTNAME/"
    echo "- Admin Panel: http://$HOSTNAME/admin/"
    echo "- API Documentation: http://$HOSTNAME/api/docs/"
    echo "- Health Check: http://$HOSTNAME/health/"
    echo ""
    info "Alternative URLs (if hostname resolution fails):"
    echo "- Main Application: http://$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")/"
    echo "- Admin Panel: http://$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")/admin/"
    echo "- API Documentation: http://$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")/api/docs/"
    echo "- Health Check: http://$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")/health/"
    echo ""
    info "Log locations:"
    echo "- Deployment log: $LOG_FILE"
    echo "- Application logs: $APP_DIR/logs/"
    echo "- Docker logs: docker-compose -f $DOCKER_COMPOSE_FILE logs"
    echo "- Current directory logs: ./logs/"
}

# Show help information
show_help() {
    echo ""
    echo "🚀 A&F Laundry Management System - Deployment Script"
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  deploy     Full deployment (default)"
    echo "  update     Update to latest version"
    echo "  backup     Create data backup"
    echo "  health     Run health check"
    echo "  logs       Show application logs"
    echo "  stop       Stop application"
    echo "  start      Start application"
    echo "  restart    Restart application"
    echo "  help       Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Full deployment"
    echo "  $0 deploy            # Full deployment"
    echo "  $0 update            # Update only"
    echo "  $0 health            # Check health"
    echo ""
    echo "Configuration:"
    echo "  Target hostname: $HOSTNAME"
    echo "  Log file: $LOG_FILE"
    echo "  Production directory: $APP_DIR"
    echo ""
}

# Main deployment function
main() {
    print_banner
    check_root
    
    log "Starting openLMS production deployment..."
    info "Log file: $LOG_FILE"
    
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

# Show help information
show_help() {
    echo ""
    echo "🚀 A&F Laundry Management System - Deployment Script"
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  deploy     Full deployment (default)"
    echo "  update     Update to latest version"
    echo "  backup     Create data backup"
    echo "  health     Run health check"
    echo "  logs       Show application logs"
    echo "  stop       Stop application"
    echo "  start      Start application"
    echo "  restart    Restart application"
    echo "  help       Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Full deployment"
    echo "  $0 deploy            # Full deployment"
    echo "  $0 update            # Update only"
    echo "  $0 health            # Check health"
    echo ""
    echo "Configuration:"
    echo "  Target hostname: $HOSTNAME"
    echo "  Log file: $LOG_FILE"
    echo "  Production directory: $APP_DIR"
    echo ""
}

# Script options
case "${1:-deploy}" in
    "deploy"|"")
        main
        ;;
    "update")
        print_banner
        check_root
        setup_repository
        backup_data
        deploy_application
        health_check
        show_status
        ;;
    "backup")
        print_banner
        check_root
        backup_data
        ;;
    "cleanup")
        print_banner
        info "Cleaning up Docker volumes and containers..."
        cd "$APP_DIR" 2>/dev/null || { error "Application directory $APP_DIR not found."; }
        docker-compose -f "$DOCKER_COMPOSE_FILE" down -v 2>/dev/null || true
        docker volume rm openlms_openlms_data openlms_openlms_logs 2>/dev/null || true
        docker volume rm openlms_data openlms_logs 2>/dev/null || true
        docker system prune -f 2>/dev/null || true
        log "Cleanup completed"
        ;;
    "health")
        print_banner
        health_check
        ;;
    "logs")
        cd "$APP_DIR" 2>/dev/null || { error "Application directory $APP_DIR not found. Run deployment first."; }
        docker-compose -f "$DOCKER_COMPOSE_FILE" logs -f
        ;;
    "stop")
        print_banner
        cd "$APP_DIR" 2>/dev/null || { error "Application directory $APP_DIR not found. Run deployment first."; }
        docker-compose -f "$DOCKER_COMPOSE_FILE" down
        ;;
    "start")
        print_banner
        cd "$APP_DIR" 2>/dev/null || { error "Application directory $APP_DIR not found. Run deployment first."; }
        docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
        ;;
    "restart")
        print_banner
        cd "$APP_DIR" 2>/dev/null || { error "Application directory $APP_DIR not found. Run deployment first."; }
        docker-compose -f "$DOCKER_COMPOSE_FILE" restart
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        echo "❌ Unknown command: $1"
        show_help
        exit 1
        ;;
esac
