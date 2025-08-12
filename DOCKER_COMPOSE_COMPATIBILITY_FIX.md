# Docker Compose Compatibility Fix

## Issue Resolved
Fixed Docker Compose version compatibility error that occurred when deploying with older Docker Compose versions (specifically version 1.25.0).

**Error Message:**
```
ERROR: Version in "./docker-compose.production.yml" is unsupported. You might be seeing this error because you're using the wrong Compose file version.
```

## Changes Made

### 1. Updated docker-compose.production.yml
- Changed version from `3.8` to `3.7` for better compatibility with older Docker Compose versions
- Version `3.7` is supported by Docker Compose 1.25.0 and newer

### 2. Enhanced deploy-production.sh
- Added Docker Compose version compatibility check
- Shows warnings for older versions (< 1.26.0)
- Provides information about using compatible compose file version

## Compatibility Matrix

| Docker Compose Version | Compose File Version | Status |
|------------------------|---------------------|---------|
| 1.25.0 - 1.25.x       | 3.7 and below      | ✅ Supported |
| 1.26.0 - 1.29.x       | 3.8 and below      | ✅ Supported |
| 2.0.0+                 | 3.8+ and others    | ✅ Fully Supported |

## Deployment Instructions

### For Production Server with Docker Compose 1.25.0

1. **Pull the latest changes:**
   ```bash
   cd /opt/openlms
   git pull origin main
   ```

2. **Run the deployment:**
   ```bash
   ./deploy-production.sh deploy
   ```

3. **Verify the deployment:**
   ```bash
   ./verify-single-container-setup.sh
   ```

### Version Check Command
You can check your Docker Compose version with:
```bash
docker-compose --version
```

## What's Included in This Fix

✅ **Backward Compatibility**: Works with Docker Compose 1.25.0+
✅ **Version Detection**: Automatic detection and warnings for older versions
✅ **Single Container Architecture**: Maintains the single container approach
✅ **Host Nginx Integration**: Still works with host-level reverse proxy

## Migration Notes

- No changes needed to existing containers or data
- The single container architecture remains unchanged
- Host nginx configuration is not affected
- All environment variables and volumes remain the same

## Testing

After deployment, verify everything works:

1. **Container Status:**
   ```bash
   docker-compose -f docker-compose.production.yml ps
   ```

2. **Health Check:**
   ```bash
   curl -f http://localhost:8080/health/
   ```

3. **Application Access:**
   ```bash
   curl -f http://af.proxysolutions.io/
   ```

## Support

If you encounter any issues:
1. Check the deployment logs: `cat logs/deploy.log`
2. Check container logs: `docker-compose -f docker-compose.production.yml logs`
3. Run the verification script: `./verify-single-container-setup.sh`

---

**Last Updated:** August 12, 2025
**Commit:** a121c62
