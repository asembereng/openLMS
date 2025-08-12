#!/bin/bash

# Verification script for single container nginx setup
# This script verifies that the old dual nginx setup is cleaned up
# and the new single container setup is working correctly

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log() {
    echo -e "${GREEN}✅ $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

echo "🔍 openLMS Single Container Setup Verification"
echo "=============================================="
echo ""

# Check for old dual nginx containers
info "Checking for old dual nginx containers..."
if docker ps -a --format "{{.Names}}" | grep -q "openlms_nginx_1"; then
    error "Found old nginx container: openlms_nginx_1"
    echo "   Run: ./deploy-production.sh cleanup-containers"
    exit 1
else
    log "No old nginx container found"
fi

if docker ps -a --format "{{.Names}}" | grep -q "openlms_web_1"; then
    info "Found container: openlms_web_1 (this should be the single container)"
    # Check if it's running
    if docker ps --format "{{.Names}}" | grep -q "openlms_web_1"; then
        log "openlms_web_1 is running (single container approach)"
    else
        warning "openlms_web_1 exists but is not running"
    fi
else
    warning "No openlms_web_1 container found - may need deployment"
fi

# Check for old volumes
info "Checking for old volumes..."
old_volumes=(
    "static_volume"
    "media_volume" 
    "openlms_openlms_data"
    "openlms_openlms_logs"
    "openlms_data"
    "openlms_logs"
)

found_old_volumes=false
for vol in "${old_volumes[@]}"; do
    if docker volume ls --format "{{.Name}}" | grep -q "^${vol}$"; then
        error "Found old volume: $vol"
        found_old_volumes=true
    fi
done

if [ "$found_old_volumes" = true ]; then
    echo "   Run: ./deploy-production.sh cleanup-containers"
    echo ""
else
    log "No old volumes found"
fi

# Check current docker-compose setup
info "Checking docker-compose configuration..."
if [ -f "docker-compose.production.yml" ]; then
    # Check if nginx service exists in compose file
    if grep -q "nginx:" docker-compose.production.yml; then
        error "docker-compose.production.yml still contains nginx service"
        echo "   This indicates dual nginx setup is still configured"
        exit 1
    else
        log "docker-compose.production.yml uses single container approach"
    fi
    
    # Check port configuration
    if grep -q "8080:80" docker-compose.production.yml; then
        log "Container configured to expose internal port 80 as external port 8080"
    else
        warning "Port configuration may need adjustment"
    fi
else
    error "docker-compose.production.yml not found"
    exit 1
fi

# Check port 8080 availability/usage
info "Checking port 8080 status..."
if lsof -i :8080 > /dev/null 2>&1; then
    # Check if it's our container
    if docker ps --format "{{.Names}} {{.Ports}}" | grep -q "8080"; then
        log "Port 8080 is being used by openLMS container"
    else
        warning "Port 8080 is in use by something other than openLMS"
        echo "   Check: lsof -i :8080"
    fi
else
    warning "Port 8080 is not in use - container may not be running"
fi

# Check host nginx configuration
info "Checking host nginx configuration..."
if [ -f "/etc/nginx/sites-available/openlms" ]; then
    log "Host nginx configuration exists: /etc/nginx/sites-available/openlms"
    
    if [ -L "/etc/nginx/sites-enabled/openlms" ]; then
        log "Host nginx site is enabled"
    else
        warning "Host nginx site exists but not enabled"
    fi
else
    warning "Host nginx configuration not found"
    echo "   Run: ./setup-host-nginx.sh"
fi

# Test container health (if running)
info "Testing container health..."
if curl -f -s --connect-timeout 3 --max-time 5 "http://127.0.0.1:8080/health/" > /dev/null 2>&1; then
    log "Container is responding on port 8080"
else
    warning "Container is not responding on port 8080"
    echo "   Container may not be running or healthy"
fi

# Test host nginx (if configured)
info "Testing host nginx proxy..."
if curl -f -s --connect-timeout 3 --max-time 5 "http://127.0.0.1/health/" > /dev/null 2>&1; then
    log "Host nginx is proxying requests correctly"
else
    warning "Host nginx proxy is not working"
    echo "   Check nginx configuration and ensure container is running"
fi

echo ""
echo "🎯 Verification Summary"
echo "======================="

# Count issues
issues=0

# Final checks
if docker ps --format "{{.Names}}" | grep -q "openlms_web_1"; then
    echo "✅ Single container (openlms_web_1) approach: ACTIVE"
else
    echo "❌ Single container not running"
    ((issues++))
fi

if ! docker ps -a --format "{{.Names}}" | grep -q "openlms_nginx_1"; then
    echo "✅ Old dual nginx setup: CLEANED UP"
else
    echo "❌ Old dual nginx containers still exist"
    ((issues++))
fi

if [ -f "/etc/nginx/sites-available/openlms" ]; then
    echo "✅ Host nginx configuration: CONFIGURED"
else
    echo "⚠️  Host nginx configuration: MISSING"
fi

if curl -f -s --connect-timeout 3 --max-time 5 "http://127.0.0.1:8080/health/" > /dev/null 2>&1; then
    echo "✅ Container health check: PASSING"
else
    echo "❌ Container health check: FAILING"
    ((issues++))
fi

echo ""
if [ $issues -eq 0 ]; then
    echo "🎉 All checks passed! Single container setup is working correctly."
    echo ""
    echo "🌐 Your application should be accessible at:"
    echo "   - http://af.proxysolutions.io (via host nginx)"
    echo "   - http://af.proxysolutions.io:8080 (direct container access)"
else
    echo "⚠️  Found $issues issues that need attention."
    echo ""
    echo "🛠️  Recommended actions:"
    echo "   1. Clean up old setup: ./deploy-production.sh cleanup-containers"
    echo "   2. Redeploy application: ./deploy-production.sh deploy"
    echo "   3. Setup host nginx: ./setup-host-nginx.sh"
fi

echo ""
