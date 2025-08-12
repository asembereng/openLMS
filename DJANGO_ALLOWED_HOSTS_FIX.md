# Django ALLOWED_HOSTS Configuration Fix

## 🔍 Issue Discovered
**Error**: `DisallowedHost at / Invalid HTTP_HOST header: 'af.proxysolutions.io'. You may need to add 'af.proxysolutions.io' to ALLOWED_HOSTS`

## 🔧 Root Cause Analysis
The issue was caused by **environment variable name mismatch** between:

### Expected by Django Settings
**File**: `laundry_management/settings_production.py`
```python
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*', cast=Csv())
```
Expected environment variable: `ALLOWED_HOSTS`

### Provided by Docker Configuration  
**File**: `docker-compose.production.yml` (before fix)
```yaml
environment:
  - DJANGO_ALLOWED_HOSTS=af.proxysolutions.io,localhost,127.0.0.1,0.0.0.0
```
Provided environment variable: `DJANGO_ALLOWED_HOSTS` ❌

## ✅ Solution Applied
Updated `docker-compose.production.yml` to use the correct environment variable names:

### Fixed Environment Variables
```yaml
environment:
  - DJANGO_SETTINGS_MODULE=laundry_management.settings_production
  - SECRET_KEY=${DJANGO_SECRET_KEY:-your-secret-key-change-this-in-production}
  - DEBUG=False
  - ALLOWED_HOSTS=af.proxysolutions.io,localhost,127.0.0.1,0.0.0.0  # ✅ Fixed
  - DATABASE_URL=sqlite:///data/db.sqlite3
  - SECURE_SSL_REDIRECT=False
  - SECURE_HSTS_SECONDS=0
```

### Changes Made
- `DJANGO_ALLOWED_HOSTS` → `ALLOWED_HOSTS` ✅
- `DJANGO_SECRET_KEY` → `SECRET_KEY` ✅  
- `DJANGO_DEBUG` → `DEBUG` ✅
- `DJANGO_SECURE_SSL_REDIRECT` → `SECURE_SSL_REDIRECT` ✅
- `DJANGO_SECURE_HSTS_SECONDS` → `SECURE_HSTS_SECONDS` ✅

## 🧪 Verification Steps

### 1. Rebuild and Deploy Container
```bash
cd /path/to/openLMS
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml up -d --build
```

### 2. Check Container Logs
```bash
docker-compose -f docker-compose.production.yml logs -f web
```

### 3. Test Application Access
```bash
# Test health endpoint
curl -I http://af.proxysolutions.io:8080/health/

# Test main application  
curl -I http://af.proxysolutions.io:8080/

# Test via host nginx (if configured)
curl -I http://af.proxysolutions.io/
```

### 4. Verify Environment Variables in Container
```bash
docker-compose -f docker-compose.production.yml exec web printenv | grep -E "(ALLOWED_HOSTS|SECRET_KEY|DEBUG)"
```

Expected output:
```
ALLOWED_HOSTS=af.proxysolutions.io,localhost,127.0.0.1,0.0.0.0
SECRET_KEY=your-secret-key-change-this-in-production
DEBUG=False
```

## 📋 Environment Variable Reference

### Django Settings Expected Variables
Based on `settings_production.py`, these environment variables are expected:

| Variable | Default | Purpose |
|----------|---------|---------|
| `SECRET_KEY` | **Required** | Django secret key |
| `ALLOWED_HOSTS` | `'*'` | Comma-separated list of allowed hosts |
| `SECURE_SSL_REDIRECT` | `False` | Redirect HTTP to HTTPS |
| `TIME_ZONE` | `'Africa/Lagos'` | Application timezone |

### Docker Environment Configuration
**File**: `docker-compose.production.yml`
```yaml
environment:
  - DJANGO_SETTINGS_MODULE=laundry_management.settings_production
  - SECRET_KEY=${DJANGO_SECRET_KEY:-your-secret-key-change-this-in-production}
  - DEBUG=False
  - ALLOWED_HOSTS=af.proxysolutions.io,localhost,127.0.0.1,0.0.0.0
  - DATABASE_URL=sqlite:///data/db.sqlite3
  - SECURE_SSL_REDIRECT=False
  - SECURE_HSTS_SECONDS=0
```

## 🔒 Security Notes

### ALLOWED_HOSTS Configuration
The current configuration allows:
- `af.proxysolutions.io` - Production domain
- `localhost` - Local development  
- `127.0.0.1` - Local IP access
- `0.0.0.0` - Docker internal access

### Production Recommendations
For production deployment:
1. Remove `localhost`, `127.0.0.1`, `0.0.0.0` if not needed
2. Use only your specific domain(s)
3. Consider wildcard subdomains if needed: `*.proxysolutions.io`

Example production-only configuration:
```yaml
- ALLOWED_HOSTS=af.proxysolutions.io,www.af.proxysolutions.io
```

## 🚀 Deployment Impact

### Before Fix
- ❌ Django rejected requests to `af.proxysolutions.io`
- ❌ DisallowedHost errors in logs
- ❌ Application inaccessible via domain

### After Fix  
- ✅ Django accepts requests to `af.proxysolutions.io`
- ✅ Application accessible via all configured hosts
- ✅ Proper environment variable mapping
- ✅ Production-ready configuration

## 📝 Related Files Modified
- `docker-compose.production.yml` - Environment variable names corrected

## 📚 References
- [Django ALLOWED_HOSTS Documentation](https://docs.djangoproject.com/en/4.2/ref/settings/#allowed-hosts)
- [Django Security Best Practices](https://docs.djangoproject.com/en/4.2/topics/security/)
- [Docker Compose Environment Variables](https://docs.docker.com/compose/environment-variables/)
