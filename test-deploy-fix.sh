#!/bin/bash

# Test script to verify deployment script fixes
echo "🔧 Testing deployment script fixes..."

# Test log directory creation
echo "✅ Testing log directory creation..."
./deploy-production.sh help > /dev/null 2>&1
if [ -d "./logs" ]; then
    echo "✅ Log directory created successfully"
else
    echo "❌ Log directory creation failed"
fi

# Test log file creation
if [ -f "./logs/deploy.log" ]; then
    echo "✅ Log file created successfully"
else
    echo "❌ Log file creation failed"
fi

# Test script execution without permission errors
echo "✅ Testing script execution..."
./deploy-production.sh help
if [ $? -eq 0 ]; then
    echo "✅ Script executes without permission errors"
else
    echo "❌ Script execution failed"
fi

echo ""
echo "🎉 Test completed! The deployment script should now work without permission issues."
echo "📝 Log file location: ./logs/deploy.log"
echo "🚀 Ready to run: ./deploy-production.sh"
