# Mnemosyne Production Deployment Guide

**Quick Links:**
- [Cloud Deployment Guide](deployment-cloud.md) - AWS, GCP, DigitalOcean, Railway, etc.
- [Multi-Tenancy Documentation](../developer/multi-tenancy.md) - User isolation and security

---

## Prerequisites

1. **Server Requirements**:
   - Ubuntu 22.04 LTS or similar
   - 4 CPU cores (minimum)
   - 8GB RAM (minimum)
   - 50GB SSD storage
   - Docker & Docker Compose installed

2. **Domain Setup**:
   - Domain name pointing to your server
   - DNS A record configured

3. **API Keys**:
   - OpenAI API key
   - (Optional) S3 credentials (AWS, DigitalOcean Spaces, etc.)
   - (Optional) Other service API keys

## Quick Start

### 1. Initial Setup

```bash
# Clone repository
git clone https://github.com/yourusername/mnemosyne.git
cd mnemosyne

# Copy environment template
cp .env.example .env.production

# Edit .env.production with your values
nano .env.production
```

### 2. Configure Environment

**CRITICAL**: Update these in `.env.production`:

```bash
# Generate secure secrets
openssl rand -hex 32  # For SECRET_KEY
openssl rand -hex 32  # For POSTGRES_PASSWORD
openssl rand -hex 32  # For REDIS_PASSWORD

# Update domain
DOMAIN=api.yourdomain.com

# Add API keys
OPENAI_API_KEY=sk-your-key-here

# Update CORS origins
CORS_ORIGINS=["https://yourdomain.com"]

# Storage Configuration (RECOMMENDED: Use S3 for production)
STORAGE_BACKEND=s3  # or "local" for development

# S3 Storage (if STORAGE_BACKEND=s3)
S3_BUCKET_NAME=mnemosyne-documents
S3_ACCESS_KEY_ID=your-s3-access-key
S3_SECRET_ACCESS_KEY=your-s3-secret-key
S3_REGION=us-east-1  # or your region
S3_ENDPOINT_URL=  # Leave empty for AWS S3
# For DigitalOcean Spaces: https://nyc3.digitaloceanspaces.com
# For MinIO: http://minio:9000
S3_PRESIGNED_URL_EXPIRY=3600  # 1 hour
```

**Storage Backend Options:**

| Backend | When to Use | Configuration |
|---------|------------|---------------|
| **S3** ✅ | Production deployments | AWS S3, DigitalOcean Spaces, MinIO |
| **Local** | Development only | File system storage |

**S3 Benefits:**
- ✅ Scalable to millions of documents
- ✅ Automatic backups and versioning
- ✅ Cost-effective ($0.023/GB/month on AWS)
- ✅ CDN integration available
- ✅ Multi-user isolation built-in

### 3. Deploy

```bash
# Run deployment script
./deploy.sh
```

This will:
- Generate SSL certificates
- Build Docker images
- Start all services
- Run database migrations
- Verify health

### 4. Set Up SSL (Let's Encrypt)

```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot certonly --standalone \
    -d api.yourdomain.com \
    --agree-tos \
    --email admin@yourdomain.com

# Update nginx to use Let's Encrypt certs
# Edit nginx/nginx.conf:
ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

# Restart nginx
docker-compose -f docker-compose.prod.yml restart nginx
```

## Service URLs

After deployment:

- **API**: https://api.yourdomain.com
- **API Docs**: https://api.yourdomain.com/docs
- **Grafana**: http://localhost:3000 (admin/your-password)
- **Prometheus**: http://localhost:9090
- **Flower (Celery)**: http://localhost:5555

## Management Commands

### View Logs

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f api
docker-compose -f docker-compose.prod.yml logs -f postgres
docker-compose -f docker-compose.prod.yml logs -f celery-worker
```

### Service Control

```bash
# Stop all
docker-compose -f docker-compose.prod.yml down

# Start all
docker-compose -f docker-compose.prod.yml up -d

# Restart specific service
docker-compose -f docker-compose.prod.yml restart api

# Scale workers
docker-compose -f docker-compose.prod.yml up -d --scale celery-worker=4
```

### Database Operations

```bash
# Backup database
./scripts/backup.sh

# Restore from backup
./scripts/restore.sh /backups/mnemosyne_backup_20240117_120000.sql.gz

# Access PostgreSQL
docker-compose -f docker-compose.prod.yml exec postgres psql -U mnemosyne -d mnemosyne
```

### Monitoring

```bash
# Check service health
curl https://api.yourdomain.com/health

# View metrics
curl http://localhost:9090/metrics

# Check Celery tasks
docker-compose -f docker-compose.prod.yml exec celery-worker celery -A backend.worker inspect active
```

## Automated Backups

Backups run daily at 2 AM (configured in docker-compose.prod.yml).

Manual backup:
```bash
docker-compose -f docker-compose.prod.yml exec backup /backup.sh
```

Backups are stored in:
- Local: `/var/lib/docker/volumes/mnemosyne_postgres_backups`
- (Optional) S3: Configure in `.env.production`

## Scaling

### Horizontal Scaling

```bash
# Add more API workers
docker-compose -f docker-compose.prod.yml up -d --scale api=3

# Add more Celery workers
docker-compose -f docker-compose.prod.yml up -d --scale celery-worker=8
```

### Vertical Scaling

Edit `docker-compose.prod.yml` to increase resource limits:

```yaml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 8G
```

## Security Checklist

- [ ] Changed all default passwords
- [ ] Generated strong `SECRET_KEY`
- [ ] SSL/TLS enabled (Let's Encrypt)
- [ ] CORS configured for your domain only
- [ ] Rate limiting enabled
- [ ] Firewall configured (allow 80, 443, block others)
- [ ] Database not exposed publicly
- [ ] Redis password protected
- [ ] Regular backups configured
- [ ] Monitoring and alerts set up

## Troubleshooting

### API not responding

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs api

# Restart API
docker-compose -f docker-compose.prod.yml restart api
```

### Database connection errors

```bash
# Check PostgreSQL
docker-compose -f docker-compose.prod.yml logs postgres

# Verify connection
docker-compose -f docker-compose.prod.yml exec api python -c "from backend.database import engine; engine.connect()"
```

### Celery tasks not processing

```bash
# Check worker status
docker-compose -f docker-compose.prod.yml logs celery-worker

# Restart workers
docker-compose -f docker-compose.prod.yml restart celery-worker
```

### Out of disk space

```bash
# Check disk usage
df -h

# Clean Docker
docker system prune -a

# Remove old backups
find /var/lib/docker/volumes/mnemosyne_postgres_backups -mtime +30 -delete
```

## Monitoring & Alerts

### Grafana Dashboards

1. Open http://localhost:3000
2. Login (admin/your-password)
3. Import dashboards from `monitoring/grafana/dashboards/`

### Prometheus Alerts

Configure alerts in `monitoring/prometheus/alerts.yml`:

```yaml
groups:
  - name: mnemosyne
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        annotations:
          summary: "High error rate detected"
```

## Updates & Maintenance

### Update Application

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

### Database Migrations

```bash
# Run migrations
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head

# Rollback migration
docker-compose -f docker-compose.prod.yml exec api alembic downgrade -1
```

## Support

- Documentation: https://docs.mnemosyne.dev
- Issues: https://github.com/yourusername/mnemosyne/issues
- Email: support@yourdomain.com
