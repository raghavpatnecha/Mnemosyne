#!/bin/bash
# Production Deployment Script

set -e

echo "=========================================="
echo "Mnemosyne Production Deployment"
echo "=========================================="

# Check if .env.production exists
if [ ! -f .env.production ]; then
    echo "ERROR: .env.production file not found!"
    echo "Please create it from .env.example and fill in all values."
    exit 1
fi

# Load environment variables
source .env.production

# Verify critical variables
REQUIRED_VARS=(
    "POSTGRES_PASSWORD"
    "REDIS_PASSWORD"
    "SECRET_KEY"
    "OPENAI_API_KEY"
    "DOMAIN"
)

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ] || [ "${!var}" == "CHANGE_ME"* ]; then
        echo "ERROR: $var is not set or still has default value!"
        echo "Please update .env.production with real values."
        exit 1
    fi
done

# Create necessary directories
echo "Creating directories..."
mkdir -p uploads logs nginx/ssl monitoring/grafana/{dashboards,datasources}

# Generate SSL certificates (self-signed for testing, use Let's Encrypt for production)
if [ ! -f nginx/ssl/cert.pem ]; then
    echo "Generating self-signed SSL certificates..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout nginx/ssl/key.pem \
        -out nginx/ssl/cert.pem \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=${DOMAIN}"

    openssl dhparam -out nginx/ssl/dhparam.pem 2048

    echo "WARNING: Using self-signed certificates. For production, use Let's Encrypt!"
fi

# Pull latest images
echo "Pulling Docker images..."
docker-compose -f docker-compose.prod.yml pull

# Build custom images
echo "Building application images..."
docker-compose -f docker-compose.prod.yml build --no-cache

# Stop existing containers
echo "Stopping existing containers..."
docker-compose -f docker-compose.prod.yml down

# Start services
echo "Starting services..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to be healthy
echo "Waiting for services to be healthy..."
sleep 10

# Check service status
echo "Checking service status..."
docker-compose -f docker-compose.prod.yml ps

# Run database migrations (if applicable)
echo "Running database migrations..."
docker-compose -f docker-compose.prod.yml exec -T api alembic upgrade head || true

# Test API health
echo "Testing API health..."
sleep 5
curl -f http://localhost/health || echo "Warning: Health check failed"

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Services:"
echo "  - API: https://${DOMAIN}"
echo "  - Docs: https://${DOMAIN}/docs"
echo "  - Grafana: http://localhost:3000"
echo "  - Prometheus: http://localhost:9090"
echo "  - Flower: http://localhost:5555"
echo ""
echo "Next steps:"
echo "  1. Configure DNS to point ${DOMAIN} to this server"
echo "  2. Set up Let's Encrypt SSL (see scripts/setup-ssl.sh)"
echo "  3. Configure monitoring alerts"
echo "  4. Set up automated backups"
echo ""
echo "View logs: docker-compose -f docker-compose.prod.yml logs -f"
echo "=========================================="
