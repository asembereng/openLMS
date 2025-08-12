#!/bin/bash

# add-allowed-host.sh
# Script to add a hostname to ALLOWED_HOSTS in a running openLMS container
# Usage: ./add-allowed-host.sh [hostname]

set -e

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

# Configuration
COMPOSE_FILE="docker-compose.production.yml"
SERVICE_NAME="web"

# Function to show usage
show_usage() {
    echo "Usage: $0 [hostname]"
    echo ""
    echo "Examples:"
    echo "  $0 af.proxysolutions.io"
    echo "  $0 mydomain.com"
    echo "  $0 192.168.1.100"
    echo ""
    echo "This script will:"
    echo "  1. Add the hostname to ALLOWED_HOSTS"
    echo "  2. Restart the Django application"
    echo "  3. Test the new hostname"
}

# Check if hostname is provided
if [ $# -eq 0 ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    show_usage
    exit 1
fi

HOSTNAME="$1"

print_status "Adding hostname '$HOSTNAME' to ALLOWED_HOSTS..."

# Validate hostname format (basic check)
if [[ ! "$HOSTNAME" =~ ^[a-zA-Z0-9.-]+$ ]]; then
    print_error "Invalid hostname format: $HOSTNAME"
    print_error "Hostname should contain only letters, numbers, dots, and hyphens"
    exit 1
fi

# Check if docker-compose file exists
if [ ! -f "$COMPOSE_FILE" ]; then
    print_error "Docker compose file not found: $COMPOSE_FILE"
    exit 1
fi

# Check if container is running
print_status "Checking if container is running..."
if ! docker-compose -f "$COMPOSE_FILE" ps | grep -q "$SERVICE_NAME.*Up"; then
    print_error "Container '$SERVICE_NAME' is not running"
    print_error "Please start the container first: docker-compose -f $COMPOSE_FILE up -d"
    exit 1
fi

print_success "Container is running"

# Get current ALLOWED_HOSTS from container
print_status "Getting current ALLOWED_HOSTS..."
CURRENT_HOSTS=$(docker-compose -f "$COMPOSE_FILE" exec -T "$SERVICE_NAME" printenv ALLOWED_HOSTS 2>/dev/null || echo "")

if [ -z "$CURRENT_HOSTS" ]; then
    print_warning "No ALLOWED_HOSTS found, using default"
    NEW_HOSTS="$HOSTNAME,localhost,127.0.0.1,0.0.0.0"
else
    # Check if hostname is already in the list
    if echo "$CURRENT_HOSTS" | grep -q "$HOSTNAME"; then
        print_warning "Hostname '$HOSTNAME' is already in ALLOWED_HOSTS: $CURRENT_HOSTS"
        print_status "Testing current configuration..."
    else
        # Add hostname to existing list
        NEW_HOSTS="$CURRENT_HOSTS,$HOSTNAME"
        print_status "Current ALLOWED_HOSTS: $CURRENT_HOSTS"
        print_status "New ALLOWED_HOSTS: $NEW_HOSTS"
    fi
fi

# Function to update environment variable in container
update_allowed_hosts() {
    local hosts="$1"
    print_status "Updating ALLOWED_HOSTS in container..."
    
    # Method 1: Try to update environment and restart via supervisor
    if docker-compose -f "$COMPOSE_FILE" exec -T "$SERVICE_NAME" which supervisorctl >/dev/null 2>&1; then
        print_status "Using supervisorctl to restart Django..."
        docker-compose -f "$COMPOSE_FILE" exec -T "$SERVICE_NAME" sh -c "
            export ALLOWED_HOSTS='$hosts'
            echo 'export ALLOWED_HOSTS=\"$hosts\"' > /tmp/new_env.sh
            source /tmp/new_env.sh
            supervisorctl restart all 2>/dev/null || supervisorctl restart gunicorn 2>/dev/null || supervisorctl restart django 2>/dev/null || echo 'Supervisor restart completed'
        "
    else
        # Method 2: Container restart if supervisor not available
        print_status "Supervisor not available, updating docker-compose and restarting container..."
        
        # Update docker-compose.yml environment section
        if grep -q "ALLOWED_HOSTS=" "$COMPOSE_FILE"; then
            # Replace existing ALLOWED_HOSTS
            sed -i.bak "s/ALLOWED_HOSTS=.*/ALLOWED_HOSTS=$hosts/" "$COMPOSE_FILE"
            print_status "Updated ALLOWED_HOSTS in $COMPOSE_FILE"
        else
            print_warning "ALLOWED_HOSTS not found in $COMPOSE_FILE, restarting with environment variable"
        fi
        
        # Restart container
        print_status "Restarting container to apply changes..."
        docker-compose -f "$COMPOSE_FILE" restart "$SERVICE_NAME"
    fi
}

# Apply the update if we have new hosts
if [ -n "$NEW_HOSTS" ] && [ "$NEW_HOSTS" != "$CURRENT_HOSTS" ]; then
    update_allowed_hosts "$NEW_HOSTS"
else
    print_status "No update needed, testing current configuration..."
fi

# Wait a moment for the application to restart
print_status "Waiting for application to restart..."
sleep 5

# Test the new hostname
print_status "Testing hostname '$HOSTNAME'..."

# Function to test hostname
test_hostname() {
    local test_host="$1"
    local test_urls=(
        "http://$test_host/health/"
        "http://$test_host/"
    )
    
    for url in "${test_urls[@]}"; do
        print_status "Testing: $url"
        
        if curl -f -s -I --connect-timeout 10 --max-time 15 "$url" >/dev/null 2>&1; then
            print_success "✅ $url - OK"
            return 0
        else
            print_warning "❌ $url - Failed"
        fi
    done
    
    return 1
}

# Test the hostname
if test_hostname "$HOSTNAME"; then
    print_success "Hostname '$HOSTNAME' successfully added to ALLOWED_HOSTS!"
    print_success "Application is accessible at:"
    echo "  - http://$HOSTNAME/"
    echo "  - http://$HOSTNAME/admin/"
    echo "  - http://$HOSTNAME/api/docs/"
else
    print_error "Failed to access application with hostname '$HOSTNAME'"
    print_error "This could be due to:"
    echo "  - DNS not pointing to this server"
    echo "  - Firewall blocking the request"
    echo "  - Application not fully restarted yet"
    echo ""
    print_status "Manual verification steps:"
    echo "  1. Check container logs: docker-compose -f $COMPOSE_FILE logs $SERVICE_NAME"
    echo "  2. Check environment: docker-compose -f $COMPOSE_FILE exec $SERVICE_NAME printenv | grep ALLOWED"
    echo "  3. Test locally: curl -H 'Host: $HOSTNAME' http://localhost:8080/"
fi

# Show current ALLOWED_HOSTS for verification
print_status "Current ALLOWED_HOSTS in container:"
docker-compose -f "$COMPOSE_FILE" exec -T "$SERVICE_NAME" printenv ALLOWED_HOSTS 2>/dev/null || print_warning "Could not retrieve ALLOWED_HOSTS"

# Show final status
print_status "Script completed. Check the output above for any errors."
