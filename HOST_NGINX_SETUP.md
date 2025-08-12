# Host-Level Nginx Reverse Proxy Setup Guide

This guide explains how to set up a host-level Nginx reverse proxy for openLMS that coexists with existing Nginx installations.

## 🎯 Architecture Overview

```
Internet → Host Nginx (Port 80) → Docker Container (Port 8080) → Django App
```

### Benefits
- **Port 80 Access**: Users can access your site without specifying a port
- **Coexistence**: Works with existing Nginx installations on port 80
- **SSL Ready**: Easy to add SSL certificates later
- **Standard Setup**: Industry-standard reverse proxy configuration

## 🚀 Quick Setup

### Automated Setup (Recommended)
The deployment script now automatically sets up host-level Nginx:

```bash
./deploy-production.sh deploy
```

### Manual Setup
If you need to set up host Nginx separately:

```bash
./setup-host-nginx.sh
```

## 📁 Configuration Files

### 1. `nginx-host.conf`
Template for host-level Nginx configuration:
- **Purpose**: Nginx configuration for the host system
- **Location**: `/etc/nginx/sites-available/openlms`
- **Features**: Security headers, gzip compression, health checks

### 2. `setup-host-nginx.sh`
Standalone script for manual host Nginx setup:
- **Purpose**: Set up host Nginx independently
- **Usage**: `./setup-host-nginx.sh`
- **Features**: Validation, backup, configuration

## 🔧 Configuration Details

### Docker Container
- **Port**: 8080 (internal to host)
- **Access**: Container accessible via `http://hostname:8080`
- **Compose File**: `docker-compose.production.yml`

### Host Nginx
- **Port**: 80 (public access)
- **Config**: `/etc/nginx/sites-available/openlms`
- **Proxy Target**: `http://127.0.0.1:8080`

## 🌐 Access URLs

After setup, your application will be accessible via:

### Primary URLs (via Host Nginx)
- **Main App**: `http://af.proxysolutions.io`
- **Admin**: `http://af.proxysolutions.io/admin`
- **API Docs**: `http://af.proxysolutions.io/api/docs`
- **Health Check**: `http://af.proxysolutions.io/health`

### Direct Container URLs (Port 8080)
- **Main App**: `http://af.proxysolutions.io:8080`
- **Admin**: `http://af.proxysolutions.io:8080/admin`
- **API Docs**: `http://af.proxysolutions.io:8080/api/docs`
- **Health Check**: `http://af.proxysolutions.io:8080/health`

## 🛠️ Management Commands

### Nginx Management
```bash
# Check nginx status
sudo systemctl status nginx

# Test nginx configuration
sudo nginx -t

# Reload nginx configuration
sudo systemctl reload nginx

# Restart nginx
sudo systemctl restart nginx

# View nginx access logs
sudo tail -f /var/log/nginx/access.log

# View nginx error logs
sudo tail -f /var/log/nginx/error.log
```

### Container Management
```bash
# Check container status
docker-compose -f docker-compose.production.yml ps

# View container logs
docker-compose -f docker-compose.production.yml logs -f

# Restart container
docker-compose -f docker-compose.production.yml restart

# Stop container
docker-compose -f docker-compose.production.yml down

# Start container
docker-compose -f docker-compose.production.yml up -d
```

## 🔍 Troubleshooting

### Port Conflicts
```bash
# Check what's using port 80
sudo lsof -i :80

# Check what's using port 8080
sudo lsof -i :8080
```

### Container Issues
```bash
# Check if container is running
curl http://127.0.0.1:8080/health/

# View container logs
docker-compose -f docker-compose.production.yml logs web
```

### Nginx Issues
```bash
# Test nginx configuration
sudo nginx -t

# Check nginx status
sudo systemctl status nginx

# View nginx error log
sudo tail -f /var/log/nginx/error.log
```

### Common Issues

1. **"Port 8080 already in use"**
   ```bash
   # Find what's using port 8080
   sudo lsof -i :8080
   
   # Kill the process or change the port in docker-compose.production.yml
   ```

2. **"Nginx test failed"**
   ```bash
   # Check syntax errors
   sudo nginx -t
   
   # View detailed error
   sudo nginx -T
   ```

3. **"502 Bad Gateway"**
   - Container might not be running on port 8080
   - Check container health: `curl http://127.0.0.1:8080/health/`
   - Check container logs: `docker-compose logs web`

4. **"Connection refused"**
   - Host nginx might not be running
   - Check nginx status: `sudo systemctl status nginx`
   - Restart nginx: `sudo systemctl restart nginx`

## 🔒 SSL/HTTPS Setup (Optional)

After the basic setup is working, you can add SSL:

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d af.proxysolutions.io

# Test automatic renewal
sudo certbot renew --dry-run
```

## 📝 Configuration Files Location

- **Host Nginx Config**: `/etc/nginx/sites-available/openlms`
- **Host Nginx Enabled**: `/etc/nginx/sites-enabled/openlms`
- **Docker Compose**: `./docker-compose.production.yml`
- **Container Config**: `./nginx.conf` (internal to container)

## 🏗️ Architecture Diagram

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Internet      │───▶│  Host Nginx      │───▶│ Docker          │
│                 │    │  (Port 80)       │    │ Container       │
│ af.proxysol...  │    │  Reverse Proxy   │    │ (Port 8080)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │                         │
                              │                         │
                              ▼                         ▼
                       ┌──────────────┐         ┌─────────────┐
                       │ Host System  │         │   Django    │
                       │ /etc/nginx/  │         │   + Nginx   │
                       │ sites-avail/ │         │   + SQLite  │
                       └──────────────┘         └─────────────┘
```

## ⚙️ Customization

### Change Hostname
Edit the configuration files to use your hostname:
```bash
# In nginx-host.conf, change:
server_name YOUR_HOSTNAME;
# to:
server_name your-domain.com;
```

### Change Container Port
Edit `docker-compose.production.yml`:
```yaml
nginx:
  ports:
    - "8080:80"  # Change 8080 to your preferred port
```

Then update the host nginx config accordingly.

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review the nginx error logs
3. Verify container health
4. Ensure all files have correct permissions
