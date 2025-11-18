#!/bin/bash

################################################################################
# Mnemosyne Production Deployment Script
# One-click deployment to cloud servers (AWS, GCP, DigitalOcean, etc.)
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Banner
echo "
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   MNEMOSYNE PRODUCTION DEPLOYMENT                         ║
║   RAG-as-a-Service Platform                               ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
"

################################################################################
# Pre-flight Checks
################################################################################

log_info "Running pre-flight checks..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed. Please install Docker first."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi
log_success "Docker installed: $(docker --version)"

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    log_error "Docker Compose is not installed. Please install Docker Compose first."
    echo "Visit: https://docs.docker.com/compose/install/"
    exit 1
fi
log_success "Docker Compose installed"

# Check if .env.production exists
if [ ! -f .env.production ]; then
    log_warning ".env.production not found. Creating from template..."
    if [ -f .env.example ]; then
        cp .env.example .env.production
        log_info "Created .env.production. Please edit it with your configuration."
        log_warning "IMPORTANT: Update the following in .env.production:"
        echo "  - SECRET_KEY (generate with: openssl rand -hex 32)"
        echo "  - POSTGRES_PASSWORD (generate with: openssl rand -hex 32)"
        echo "  - REDIS_PASSWORD (generate with: openssl rand -hex 32)"
        echo "  - OPENAI_API_KEY (your OpenAI API key)"
        echo "  - DOMAIN (your domain name)"
        echo "  - STORAGE_BACKEND (set to 's3' for production)"
        echo "  - S3 settings (if using S3 storage)"
        read -p "Press Enter after updating .env.production to continue..."
    else
        log_error ".env.example not found. Cannot create .env.production"
        exit 1
    fi
fi

# Validate critical environment variables
log_info "Validating environment configuration..."

# Source the .env.production file
set -a
source .env.production
set +a

# Check critical variables
MISSING_VARS=()

[ -z "$SECRET_KEY" ] || [ "$SECRET_KEY" == "CHANGE_ME_TO_RANDOM_32_BYTE_HEX" ] && MISSING_VARS+=("SECRET_KEY")
[ -z "$POSTGRES_PASSWORD" ] || [ "$POSTGRES_PASSWORD" == "CHANGE_ME_TO_STRONG_PASSWORD" ] && MISSING_VARS+=("POSTGRES_PASSWORD")
[ -z "$REDIS_PASSWORD" ] || [ "$REDIS_PASSWORD" == "CHANGE_ME_TO_STRONG_PASSWORD" ] && MISSING_VARS+=("REDIS_PASSWORD")
[ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" == "sk-your-openai-api-key-here" ] && MISSING_VARS+=("OPENAI_API_KEY")

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    log_error "The following required variables are not set in .env.production:"
    for var in "${MISSING_VARS[@]}"; do
        echo "  - $var"
    done
    log_info "Generate secure values with: openssl rand -hex 32"
    exit 1
fi

log_success "Environment configuration validated"

################################################################################
# Storage Configuration Check
################################################################################

log_info "Checking storage configuration..."

if [ "$STORAGE_BACKEND" == "s3" ]; then
    log_info "S3 storage backend detected"

    # Check S3 configuration
    S3_MISSING=()
    [ -z "$S3_BUCKET_NAME" ] && S3_MISSING+=("S3_BUCKET_NAME")
    [ -z "$S3_REGION" ] && S3_MISSING+=("S3_REGION")

    if [ ${#S3_MISSING[@]} -ne 0 ]; then
        log_error "S3 backend selected but missing required variables:"
        for var in "${S3_MISSING[@]}"; do
            echo "  - $var"
        done
        exit 1
    fi

    log_success "S3 storage configured: bucket=$S3_BUCKET_NAME, region=$S3_REGION"
else
    log_info "Local file storage configured"
    log_warning "RECOMMENDATION: Use S3 storage for production deployments"
fi

################################################################################
# Deployment Options
################################################################################

echo ""
log_info "Select deployment mode:"
echo "  1) Full production (API + Workers + Database + Redis + Monitoring)"
echo "  2) API only (assumes external database/redis)"
echo "  3) Development mode"
echo "  4) Update existing deployment (pull + rebuild)"
echo "  5) Backup data before deployment"

read -p "Enter choice [1-5]: " DEPLOY_MODE

case $DEPLOY_MODE in
    1)
        COMPOSE_FILE="docker-compose.prod.yml"
        log_info "Full production deployment selected"
        ;;
    2)
        COMPOSE_FILE="docker-compose.prod.yml"
        SERVICES="api celery-worker celery-beat nginx"
        log_info "API-only deployment selected"
        ;;
    3)
        COMPOSE_FILE="docker-compose.yml"
        log_info "Development deployment selected"
        ;;
    4)
        log_info "Update mode selected"
        UPDATE_MODE=true
        COMPOSE_FILE="docker-compose.prod.yml"
        ;;
    5)
        log_info "Running backup first..."
        bash scripts/backup-complete.sh
        COMPOSE_FILE="docker-compose.prod.yml"
        ;;
    *)
        log_error "Invalid choice"
        exit 1
        ;;
esac

################################################################################
# Backup Existing Data
################################################################################

if [ "$UPDATE_MODE" == "true" ]; then
    log_info "Backing up existing data..."
    docker-compose -f $COMPOSE_FILE exec -T postgres pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup_$(date +%Y%m%d_%H%M%S).sql
    log_success "Database backup created"
fi

################################################################################
# Build and Deploy
################################################################################

log_info "Building Docker images..."
if [ -n "$SERVICES" ]; then
    docker-compose -f $COMPOSE_FILE build $SERVICES
else
    docker-compose -f $COMPOSE_FILE build
fi
log_success "Docker images built successfully"

log_info "Starting services..."
if [ -n "$SERVICES" ]; then
    docker-compose -f $COMPOSE_FILE up -d $SERVICES
else
    docker-compose -f $COMPOSE_FILE up -d
fi
log_success "Services started"

################################################################################
# Database Migrations
################################################################################

log_info "Waiting for database to be ready..."
sleep 10

log_info "Running database migrations..."
docker-compose -f $COMPOSE_FILE exec -T api alembic upgrade head
log_success "Database migrations completed"

################################################################################
# Health Checks
################################################################################

log_info "Running health checks..."

# Wait for services to be healthy
MAX_WAIT=120
WAITED=0

while [ $WAITED -lt $MAX_WAIT ]; do
    if docker-compose -f $COMPOSE_FILE ps | grep -q "healthy"; then
        log_success "Services are healthy"
        break
    fi
    echo -n "."
    sleep 5
    WAITED=$((WAITED + 5))
done

if [ $WAITED -ge $MAX_WAIT ]; then
    log_warning "Timeout waiting for services to be healthy"
    log_info "Check service logs with: docker-compose -f $COMPOSE_FILE logs"
fi

################################################################################
# Post-Deployment Information
################################################################################

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║   DEPLOYMENT COMPLETE!                                    ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

log_success "Mnemosyne is now running!"
echo ""
log_info "Service URLs:"
echo "  - API: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
echo "  - Grafana: http://localhost:3000 (admin/${GRAFANA_ADMIN_PASSWORD:-admin})"
echo "  - Flower (Celery): http://localhost:5555"
echo "  - Prometheus: http://localhost:9090"
echo ""

log_info "Useful commands:"
echo "  - View logs: docker-compose -f $COMPOSE_FILE logs -f"
echo "  - View status: docker-compose -f $COMPOSE_FILE ps"
echo "  - Stop services: docker-compose -f $COMPOSE_FILE down"
echo "  - Restart: docker-compose -f $COMPOSE_FILE restart"
echo "  - Shell access: docker-compose -f $COMPOSE_FILE exec api bash"
echo ""

log_info "Next steps:"
echo "  1. Set up SSL certificates (see docs/user/deployment.md)"
echo "  2. Configure DNS to point to this server"
echo "  3. Set up automated backups"
echo "  4. Configure monitoring alerts"
echo "  5. Test API endpoints"
echo ""

if [ "$STORAGE_BACKEND" == "local" ]; then
    log_warning "You are using local file storage."
    log_info "For production, configure S3 storage:"
    echo "  1. Set STORAGE_BACKEND=s3 in .env.production"
    echo "  2. Configure S3_* variables"
    echo "  3. Redeploy with: ./deploy.sh"
    echo ""
fi

log_success "Deployment completed successfully! 🚀"
