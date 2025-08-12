#!/bin/bash

# Manual Host-Level Nginx Setup Script for openLMS
# This script sets up host-level nginx reverse proxy for openLMS container

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
HOSTNAME="af.proxysolutions.io"
CONTAINER_PORT="8080"

# Functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

echo "🌐 Setting up Host-Level Nginx Reverse Proxy for openLMS"
echo "========================================================"
echo ""

# Check if running as root or with sudo
if [[ $EUID -ne 0 ]] && ! sudo -n true 2>/dev/null; then
    error "This script requires sudo privileges to configure nginx. Please run with sudo or ensure sudo is configured."
fi

# Check if nginx is installed
if ! command -v nginx &> /dev/null; then
    error "Nginx is not installed. Please install nginx first:
  Ubuntu/Debian: sudo apt-get install nginx
  CentOS/RHEL: sudo yum install nginx
  Fedora: sudo dnf install nginx"
fi

# Check if nginx config template exists
if [ ! -f "nginx-host.conf" ]; then
    error "nginx-host.conf template not found. Please run this script from the openLMS project directory."
fi

# Check if container is running on port 8080
if ! curl -f -s --connect-timeout 3 --max-time 5 "http://127.0.0.1:$CONTAINER_PORT/health/" > /dev/null 2>&1; then
    warning "openLMS container doesn't seem to be running on port $CONTAINER_PORT."
    echo "Please ensure the container is running before continuing."
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

info "Configuring host-level nginx reverse proxy..."

# Backup existing nginx configuration
if [ -f "/etc/nginx/sites-enabled/default" ]; then
    info "Backing up default nginx site..."
    sudo cp /etc/nginx/sites-enabled/default /etc/nginx/sites-available/default.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
fi

# Copy and configure the nginx host config
nginx_config="/etc/nginx/sites-available/openlms"
nginx_enabled="/etc/nginx/sites-enabled/openlms"

info "Creating nginx configuration for $HOSTNAME..."
sudo cp nginx-host.conf "$nginx_config"
sudo sed -i "s/YOUR_HOSTNAME/$HOSTNAME/g" "$nginx_config"

# Enable the site
info "Enabling openLMS nginx site..."
sudo ln -sf "$nginx_config" "$nginx_enabled" 2>/dev/null || true

# Remove default nginx site
info "Disabling default nginx site..."
sudo rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true

# Test nginx configuration
info "Testing nginx configuration..."
if sudo nginx -t; then
    log "✅ Nginx configuration test passed"
    
    # Reload nginx to apply changes
    info "Reloading nginx..."
    if sudo systemctl reload nginx; then
        log "✅ Host-level Nginx reverse proxy configured successfully!"
        echo ""
        echo "🎉 Setup Complete!"
        echo "=================="
        echo ""
        echo "Your openLMS application is now accessible at:"
        echo "  🌐 http://$HOSTNAME"
        echo "  🔧 http://$HOSTNAME/admin"
        echo "  📚 http://$HOSTNAME/api/docs"
        echo "  ❤️  http://$HOSTNAME/health"
        echo ""
        echo "Container direct access (port $CONTAINER_PORT):"
        echo "  🌐 http://$HOSTNAME:$CONTAINER_PORT"
        echo ""
        echo "📝 Configuration details:"
        echo "  - Nginx config: $nginx_config"
        echo "  - Container port: $CONTAINER_PORT"
        echo "  - Host nginx forwards requests to: 127.0.0.1:$CONTAINER_PORT"
        echo ""
        echo "🛠️  Management commands:"
        echo "  - Check nginx status: sudo systemctl status nginx"
        echo "  - Reload nginx: sudo systemctl reload nginx"
        echo "  - View nginx logs: sudo tail -f /var/log/nginx/access.log"
        echo ""
    else
        error "❌ Failed to reload nginx. Please check the configuration manually."
    fi
else
    error "❌ Nginx configuration test failed. Please check the configuration manually."
fi
