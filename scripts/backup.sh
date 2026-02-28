#!/bin/sh
# =============================================================================
# IIT ML Service - Automated Backup Script
# =============================================================================
# This script performs automated backups of PostgreSQL database and model files
# Usage: Run via cron or manually
# =============================================================================

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/backups}"
POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-iit_ml_service}"
POSTGRES_USER="${POSTGRES_USER:-ml_service_user}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/var/log/backup.log"

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}/postgres"
mkdir -p "${BACKUP_DIR}/models"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# =============================================================================
# Database Backup
# =============================================================================
backup_database() {
    log "Starting database backup..."
    
    # Set PGPASSWORD for pg_dump
    export PGPASSWORD="$POSTGRES_PASSWORD"
    
    # Perform backup
    pg_dump -h "$POSTGRES_HOST" \
            -U "$POSTGRES_USER" \
            -d "$POSTGRES_DB" \
            --format=custom \
            --compress=9 \
            --file="${BACKUP_DIR}/postgres/iit_ml_service_${TIMESTAMP}.dump"
    
    if [ $? -eq 0 ]; then
        log "Database backup completed: iit_ml_service_${TIMESTAMP}.dump"
    else
        log "ERROR: Database backup failed!"
        return 1
    fi
    
    unset PGPASSWORD
}

# =============================================================================
# Model Files Backup
# =============================================================================
backup_models() {
    log "Starting model files backup..."
    
    if [ -d "/app/models" ]; then
        tar -czf "${BACKUP_DIR}/models/models_${TIMESTAMP}.tar.gz" -C /app models/
        
        if [ $? -eq 0 ]; then
            log "Model backup completed: models_${TIMESTAMP}.tar.gz"
        else
            log "ERROR: Model backup failed!"
            return 1
        fi
    else
        log "WARNING: Model directory not found, skipping model backup"
    fi
}

# =============================================================================
# Cleanup Old Backups
# =============================================================================
cleanup_old_backups() {
    log "Cleaning up backups older than ${RETENTION_DAYS} days..."
    
    # Clean up old database backups
    find "${BACKUP_DIR}/postgres" -name "*.dump" -type f -mtime +${RETENTION_DAYS} -delete
    
    # Clean up old model backups
    find "${BACKUP_DIR}/models" -name "*.tar.gz" -type f -mtime +${RETENTION_DAYS} -delete
    
    log "Cleanup completed"
}

# =============================================================================
# Backup Verification
# =============================================================================
verify_backup() {
    log "Verifying latest backup..."
    
    LATEST_DB_BACKUP=$(ls -t "${BACKUP_DIR}/postgres"/*.dump 2>/dev/null | head -1)
    
    if [ -n "$LATEST_DB_BACKUP" ]; then
        SIZE=$(stat -f%z "$LATEST_DB_BACKUP" 2>/dev/null || stat -c%s "$LATEST_DB_BACKUP" 2>/dev/null)
        
        if [ "$SIZE" -gt 1000 ]; then
            log "Backup verification passed: $(basename "$LATEST_DB_BACKUP") ($SIZE bytes)"
            return 0
        else
            log "WARNING: Backup file seems too small: $(basename "$LATEST_DB_BACKUP") ($SIZE bytes)"
            return 1
        fi
    else
        log "ERROR: No backup file found!"
        return 1
    fi
}

# =============================================================================
# Main Execution
# =============================================================================
main() {
    log "========== Backup started =========="
    
    # Run backups
    backup_database
    backup_models
    
    # Verify
    verify_backup
    
    # Cleanup
    cleanup_old_backups
    
    log "========== Backup completed =========="
}

# Run main function
main "$@"

exit 0
