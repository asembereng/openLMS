# Container Logging Issue Resolution

## Issue Summary
**Problem**: Django container was failing to start with the error:
```
ValueError: Unable to configure handler 'file'
FileNotFoundError: [Errno 2] No such file or directory: '/app/data/logs/django.log'
```

**Root Cause**: The logging configuration in `settings_production.py` was trying to write to `/app/data/logs/django.log`, but the directory `/app/data/logs/` was not being created during container startup.

## ✅ **Fixed Components**

### 1. **Dockerfile.production** 
- **Change**: Updated startup script to create `/app/data/logs` directory
- **Before**: `mkdir -p /app/data`
- **After**: `mkdir -p /app/data/logs`

### 2. **settings_production.py**
- **Enhancement**: Added robust logging configuration with fallback
- **Features**:
  - Automatic log directory creation with error handling
  - Graceful fallback to console-only logging if file logging fails
  - Dynamic handler configuration based on directory availability

## 🔧 **Technical Implementation**

### Dockerfile Changes
```bash
# Before
mkdir -p /app/data

# After  
mkdir -p /app/data/logs
```

### Settings Changes
```python
# Before: Fixed file handler that could fail
LOGGING = {
    'handlers': {
        'file': {
            'filename': BASE_DIR / 'data' / 'logs' / 'django.log',
            # ... other config
        },
    },
    'root': {
        'handlers': ['console', 'file'],  # Fixed handlers
    }
}

# After: Dynamic configuration with fallback
log_dir = BASE_DIR / 'data' / 'logs'
try:
    log_dir.mkdir(parents=True, exist_ok=True)
except (OSError, PermissionError):
    pass  # Fallback to console logging

LOGGING = {
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],  # Start with console only
    }
}

# Add file handler only if directory is writable
if log_dir.exists() and os.access(log_dir, os.W_OK):
    LOGGING['handlers']['file'] = { ... }
    LOGGING['root']['handlers'].append('file')
```

## 🚀 **Deployment Instructions**

### For Production Server:

1. **Pull Latest Changes:**
   ```bash
   cd /opt/openlms
   git pull origin main
   ```

2. **Rebuild and Deploy:**
   ```bash
   ./deploy-production.sh deploy
   ```

3. **Verify Container Startup:**
   ```bash
   docker-compose -f docker-compose.production.yml logs -f web
   ```

### Expected Startup Log Output:
```
Starting openLMS Production Container...
Setting up data directory...
Running database migrations...
[Django logs will appear here without errors]
```

## 🔍 **Verification Steps**

1. **Check Container Status:**
   ```bash
   docker-compose -f docker-compose.production.yml ps
   ```

2. **Test Health Endpoint:**
   ```bash
   curl -f http://localhost:8080/health/
   ```

3. **Verify Log Files:**
   ```bash
   ls -la data/logs/
   # Should show django.log if file logging is working
   ```

4. **Test Application Access:**
   ```bash
   curl -f http://af.proxysolutions.io/
   ```

## 📊 **Benefits of This Fix**

✅ **Container Reliability**: No more startup failures due to missing directories
✅ **Graceful Degradation**: Falls back to console logging if file system issues occur  
✅ **Production Ready**: Robust error handling for various deployment scenarios
✅ **Debugging Friendly**: Clear logging output for troubleshooting
✅ **Maintenance Free**: Automatic directory creation and permission handling

## 🛠️ **Troubleshooting**

If you still encounter issues:

1. **Check Permissions:**
   ```bash
   docker-compose -f docker-compose.production.yml exec web ls -la /app/data/
   ```

2. **View Container Logs:**
   ```bash
   docker logs --tail 50 <container_id>
   ```

3. **Test Log Directory Creation:**
   ```bash
   docker-compose -f docker-compose.production.yml exec web mkdir -p /app/data/logs
   ```

---

**Status**: ✅ **RESOLVED**  
**Commit**: `342e7cd` - Container logging issue fixed  
**Ready for Production**: Yes  
**Date**: August 12, 2025
