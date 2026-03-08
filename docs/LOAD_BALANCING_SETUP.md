# Load Balancing Setup Guide

This guide explains how to deploy the IIT ML Service with nginx load balancing for high availability and scalability.

## Overview

The load balanced configuration includes:
- **3 primary backend instances** for handling production traffic
- **1 backup instance** that activates when all primaries are down
- **nginx load balancer** with health checks and automatic failover
- **Session affinity** for authentication endpoints
- **Rate limiting** per endpoint type
- **Response caching** for API endpoints

## Architecture

```
                    ┌─────────────┐
                    │   Client    │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │    Nginx    │
                    │  Load Bal.  │
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
┌───────▼───────┐ ┌───────▼───────┐ ┌───────▼───────┐
│  ML Service 1 │ │  ML Service 2 │ │  ML Service 3 │
│   Port 8000   │ │   Port 8001   │ │   Port 8002   │
└───────┬───────┘ └───────┬───────┘ └───────┬───────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
┌───────▼───────┐ ┌───────▼───────┐ ┌───────▼───────┐
│  PostgreSQL   │ │    Redis     │ │   Backup ML   │
│   Port 5432   │ │   Port 6379   │ │  Port 8003    │
└───────────────┘ └───────────────┘ └───────────────┘
```

## Quick Start

### 1. Using Docker Compose (Recommended)

```bash
# Start all services
docker-compose -f docker-compose.load-balanced.yml up -d

# Check service health
docker-compose -f docker-compose.load-balanced.yml ps

# View logs
docker-compose -f docker-compose.load-balanced.yml logs -f nginx

# Stop services
docker-compose -f docker-compose.load-balanced.yml down
```

### 2. Environment Variables

Create a `.env` file or set environment variables:

```bash
# Database
POSTGRES_PASSWORD=your_secure_password_here

# Security
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production

# CORS
CORS_ORIGINS=["https://yourdomain.com","https://www.yourdomain.com"]

# Error Tracking (optional)
SENTRY_DSN=https://your-dsn@sentry.io/project-id

# Grafana
GRAFANA_USER=admin
GRAFANA_PASSWORD=your_grafana_password
```

## Load Balancing Configuration

### Upstream Configuration

The nginx configuration uses the **least_conn** load balancing method, which directs requests to the server with the fewest active connections:

```nginx
upstream ml_service_backend {
    least_conn;
    
    server ml-service-1:8000 max_fails=3 fail_timeout=30s weight=1;
    server ml-service-2:8001 max_fails=3 fail_timeout=30s weight=1;
    server ml-service-3:8002 max_fails=3 fail_timeout=30s weight=1;
    server ml-service-backup:8003 backup;
    
    keepalive 32;
}
```

### Health Checks

- **Backend health**: Each ML service instance has a `/health` endpoint
- **nginx health check**: Checks backend availability every 30 seconds
- **Failover**: After 3 failed attempts within 30 seconds, a server is marked down

### Session Affinity

For authentication endpoints, we use **ip_hash** for sticky sessions:

```nginx
upstream ml_service_backend_sticky {
    ip_hash;
    server ml-service-1:8000;
    server ml-service-2:8001;
    server ml-service-3:8002;
}
```

This ensures that a client's auth requests always go to the same backend instance.

## Rate Limiting

Different endpoints have different rate limits:

| Endpoint Zone | Rate Limit | Burst |
|--------------|-----------|-------|
| General API | 10 req/s | 20 |
| Auth | 5 req/s | 5 |
| Predictions | 20 req/s | 50 |

## Caching

### API Response Caching

- **Cache location**: `/var/cache/nginx/api_cache`
- **Cache size**: 100MB
- **Cache duration**: 5 minutes for successful responses
- **Bypass**: POST, PUT, DELETE, PATCH requests are never cached

### Static File Caching

- **Cache location**: `/var/cache/nginx/static_cache`
- **Cache size**: 500MB
- **Cache duration**: 1 year
- **Headers**: `Cache-Control: public, immutable`

## Monitoring

### Prometheus Metrics

Access Prometheus at `http://localhost:9090`

### Grafana Dashboard

Access Grafana at `http://localhost:3001`
- Default credentials: `admin / admin` (change in production)

### Nginx Status

Access nginx status at `http://localhost:8080/nginx_status` (localhost only)

## Scaling

### Horizontal Scaling

To add more backend instances:

1. **Add new service to docker-compose**:
```yaml
ml-service-4:
  build:
    context: ./backend/ml-service
    dockerfile: Dockerfile
  ports:
    - "8004:8000"
  # ... same configuration as other instances
```

2. **Update nginx upstream**:
```nginx
upstream ml_service_backend {
    server ml-service-1:8000;
    server ml-service-2:8001;
    server ml-service-3:8002;
    server ml-service-4:8004;  # New instance
}
```

3. **Restart nginx**:
```bash
docker-compose -f docker-compose.load-balanced.yml restart nginx
```

### Vertical Scaling

To increase resources for existing instances:

```yaml
ml-service-1:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 2G
      reservations:
        cpus: '1'
        memory: 1G
```

## SSL/TLS Configuration

### Using Let's Encrypt

1. **Install certbot**:
```bash
sudo apt-get install certbot python3-certbot-nginx
```

2. **Generate certificates**:
```bash
sudo certbot certonly --nginx -d yourdomain.com -d www.yourdomain.com
```

3. **Update nginx configuration**:
```nginx
ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
```

### Self-Signed Certificates (Development)

Generate self-signed certificates:

```bash
mkdir -p nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem \
  -out nginx/ssl/cert.pem \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
```

## Troubleshooting

### Check Backend Health

```bash
# Check individual backend
curl http://localhost:8000/health

# Check through nginx
curl http://localhost/health
```

### View Nginx Logs

```bash
# Access logs
docker-compose -f docker-compose.load-balanced.yml logs nginx | grep ml_service_access

# Error logs
docker-compose -f docker-compose.load-balanced.yml logs nginx | grep ml_service_error
```

### Test Load Balancing

```bash
# Make multiple requests and check distribution
for i in {1..10}; do
  curl -s http://localhost/health | grep -o "instance_[0-9]"
done
```

### Common Issues

**Issue**: 502 Bad Gateway
- **Cause**: Backend service is down
- **Fix**: Check backend logs and restart if needed

**Issue**: Uneven load distribution
- **Cause**: Using ip_hash with few clients
- **Fix**: Switch to least_conn or round_robin

**Issue**: High memory usage
- **Cause**: Too many keepalive connections
- **Fix**: Reduce `keepalive` value in upstream config

## Production Checklist

- [ ] Change all default passwords
- [ ] Configure SSL/TLS certificates
- [ ] Set up firewall rules
- [ ] Configure backup strategy
- [ ] Set up monitoring alerts
- [ ] Test failover scenarios
- [ ] Configure log rotation
- [ ] Set up automated deployment
- [ ] Document runbooks
- [ ] Perform load testing

## Performance Tuning

### Nginx Worker Processes

Edit `nginx/nginx-load-balanced.conf`:

```nginx
worker_processes auto;
worker_rlimit_nofile 65535;

events {
    worker_connections 4096;
    use epoll;
}
```

### Backend Workers

Increase uvicorn workers in `backend/ml-service/Dockerfile`:

```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Database Connection Pool

Adjust in `backend/ml-service/app/config.py`:

```python
pool_size=20,
max_overflow=40,
pool_pre_ping=True,
```

## Additional Resources

- [nginx Load Balancing Guide](https://docs.nginx.com/nginx/admin-guide/load-balancer/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
