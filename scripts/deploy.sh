#!/bin/bash
# Production Deployment Script for IIT ML Service
# This script automates the deployment process

set -e  # Exit on error
set -o pipefail  # Exit on pipe failure

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${PROJECT_ROOT}/.env.production"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.prod.yml"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi
    
    # Check if .env.production exists
    if [ ! -f "$ENV_FILE" ]; then
        log_error ".env.production file not found"
        exit 1
    fi
    
    log_info "Prerequisites check passed"
}

load_env_vars() {
    log_info "Loading environment variables..."
    export $(cat "$ENV_FILE" | grep -v '^#' | xargs)
}

build_images() {
    log_info "Building Docker images..."
    
    # Build backend
    log_info "Building backend image..."
    cd "${PROJECT_ROOT}/backend/ml-service"
    docker build -t ${DOCKER_USERNAME}/iit-ml-backend:${IMAGE_TAG} .
    
    # Build frontend
    log_info "Building frontend image..."
    cd "${PROJECT_ROOT}"
    docker build -t ${DOCKER_USERNAME}/iit-ml-frontend:${IMAGE_TAG} .
    
    log_info "Images built successfully"
}

push_images() {
    log_info "Pushing Docker images to registry..."
    
    # Login to registry
    echo "${DOCKER_PASSWORD}" | docker login -u "${DOCKER_USERNAME}" --password-stdin
    
    # Push images
    docker push ${DOCKER_USERNAME}/iit-ml-backend:${IMAGE_TAG}
    docker push ${DOCKER_USERNAME}/iit-ml-frontend:${IMAGE_TAG}
    
    log_info "Images pushed successfully"
}

run_migrations() {
    log_info "Running database migrations..."
    
    cd "${PROJECT_ROOT}"
    docker-compose -f "$COMPOSE_FILE" exec -T backend alembic upgrade head
    
    log_info "Migrations completed"
}

deploy_services() {
    log_info "Deploying services..."
    
    cd "${PROJECT_ROOT}"
    
    # Stop existing services
    log_info "Stopping existing services..."
    docker-compose -f "$COMPOSE_FILE" down
    
    # Start new services
    log_info "Starting new services..."
    docker-compose -f "$COMPOSE_FILE" up -d
    
    log_info "Services deployed"
}

health_check() {
    log_info "Running health checks..."
    
    local max_attempts=30
    local attempt=1
    local health_url="${API_URL:-https://iit-ml.example.com}/health"
    
    while [ $attempt -le $max_attempts ]; do
        log_info "Health check attempt $attempt/$max_attempts..."
        
        if curl -f -s "$health_url" > /dev/null 2>&1; then
            log_info "Health check passed!"
            return 0
        fi
        
        sleep 10
        attempt=$((attempt + 1))
    done
    
    log_error "Health check failed after $max_attempts attempts"
    return 1
}

rollback() {
    log_warn "Initiating rollback..."
    
    cd "${PROJECT_ROOT}"
    docker-compose -f "$COMPOSE_FILE" down
    docker-compose -f "$COMPOSE_FILE" up -d
    
    log_warn "Rollback completed"
}

create_backup() {
    log_info "Creating backup..."
    
    local backup_dir="${PROJECT_ROOT}/backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    # Backup database
    docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}" > "${backup_dir}/database.sql"
    
    # Backup models
    docker cp iit-ml-backend:/app/models "${backup_dir}/"
    
    log_info "Backup created at $backup_dir"
}

main() {
    log_info "Starting deployment process..."
    
    # Parse command line arguments
    SKIP_BUILD=false
    SKIP_PUSH=false
    SKIP_MIGRATIONS=false
    CREATE_BACKUP=true
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-build)
                SKIP_BUILD=true
                shift
                ;;
            --skip-push)
                SKIP_PUSH=true
                shift
                ;;
            --skip-migrations)
                SKIP_MIGRATIONS=true
                shift
                ;;
            --no-backup)
                CREATE_BACKUP=false
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  --skip-build       Skip building images"
                echo "  --skip-push        Skip pushing images"
                echo "  --skip-migrations  Skip database migrations"
                echo "  --no-backup        Skip creating backup"
                echo "  --help             Show this help message"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Execute deployment steps
    check_prerequisites
    load_env_vars
    
    if [ "$CREATE_BACKUP" = true ]; then
        create_backup
    fi
    
    if [ "$SKIP_BUILD" = false ]; then
        build_images
    fi
    
    if [ "$SKIP_PUSH" = false ]; then
        push_images
    fi
    
    deploy_services
    
    if [ "$SKIP_MIGRATIONS" = false ]; then
        run_migrations
    fi
    
    if health_check; then
        log_info "Deployment completed successfully!"
        exit 0
    else
        log_error "Deployment failed health check"
        rollback
        exit 1
    fi
}

# Run main function
main "$@"
