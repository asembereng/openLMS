#!/bin/bash

# quick-add-host.sh
# Quick script to add hostname to ALLOWED_HOSTS in running container
# Usage: ./quick-add-host.sh [hostname]

set -e

if [ $# -eq 0 ]; then
    echo "Usage: $0 [hostname]"
    echo "Example: $0 af.proxysolutions.io"
    exit 1
fi

HOSTNAME="$1"
COMPOSE_FILE="docker-compose.production.yml"

echo "🔧 Adding '$HOSTNAME' to ALLOWED_HOSTS..."

# Get current hosts
CURRENT=$(docker-compose -f "$COMPOSE_FILE" exec -T web printenv ALLOWED_HOSTS 2>/dev/null || echo "localhost,127.0.0.1")

# Add new hostname if not already present
if echo "$CURRENT" | grep -q "$HOSTNAME"; then
    echo "✅ Hostname '$HOSTNAME' already in ALLOWED_HOSTS"
    NEW_HOSTS="$CURRENT"
else
    NEW_HOSTS="$CURRENT,$HOSTNAME"
    echo "📝 Updating: $CURRENT → $NEW_HOSTS"
fi

# Update docker-compose.yml
sed -i.bak "s/ALLOWED_HOSTS=.*/ALLOWED_HOSTS=$NEW_HOSTS/" "$COMPOSE_FILE"

# Restart container
echo "🔄 Restarting container..."
docker-compose -f "$COMPOSE_FILE" restart web

# Wait and test
echo "⏳ Waiting for restart..."
sleep 5

echo "🧪 Testing hostname..."
if curl -f -s -I "http://$HOSTNAME/health/" >/dev/null 2>&1; then
    echo "✅ SUCCESS: http://$HOSTNAME/ is now accessible!"
else
    echo "❌ Test failed - check logs: docker-compose -f $COMPOSE_FILE logs web"
fi

echo "📋 Current ALLOWED_HOSTS:"
docker-compose -f "$COMPOSE_FILE" exec -T web printenv ALLOWED_HOSTS 2>/dev/null || echo "Could not retrieve"
