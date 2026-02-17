"""
Backup and restore API endpoints for IIT ML Service
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any, Optional
import logging
import os
from datetime import datetime

from ..utils.database import backup_database, restore_database, check_database_health
from ..config import get_settings
from ..auth import get_current_user
from ..models import User

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/backup", tags=["backup"])

@router.post("/database/backup",
            summary="Create Database Backup",
            description="""Create a backup of the application database.

            **Backup Process:**
            1. **Backup Name Generation**: Auto-generates timestamped backup name or uses custom name
            2. **Database Copy**: Creates full copy of database file
            3. **Storage**: Saves backup to configured backup directory
            4. **Metadata**: Records backup size and creation timestamp

            **Backup Contents:**
            - Complete database schema and data
            - All tables: patients, predictions, users, ensembles, etc.
            - Relationships and constraints
            - Indexes and triggers

            **Storage Location:**
            - Configured backup directory (settings.backup_dir)
            - File format: {backup_name}.db
            - Automatic directory creation if needed

            **Security:**
            - Requires admin privileges
            - Backup files inherit system file permissions
            - Sensitive healthcare data protection

            **Use Cases:**
            - Regular database backups for disaster recovery
            - Pre-deployment backups before major changes
            - Data migration and export
            - Compliance and audit trail requirements

            **Performance:**
            - Backup duration depends on database size
            - Minimal impact on system performance
            - Non-blocking operation for active requests
            """,
            responses={
                200: {
                    "description": "Database backup created successfully",
                    "content": {
                        "application/json": {
                            "example": {
                                "message": "Database backup created successfully",
                                "backup_path": "/backups/backup_20250115_103000.db",
                                "backup_name": "backup_20250115_103000",
                                "file_size_bytes": 2048000,
                                "created_at": "2025-01-15T10:30:00"
                            }
                        }
                    }
                },
                403: {
                    "description": "Admin privileges required"
                },
                500: {
                    "description": "Internal server error during backup creation"
                }
            })
async def create_database_backup(
    background_tasks: BackgroundTasks,
    backup_name: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Create a database backup

    Requires admin privileges
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        # Generate backup filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_name = backup_name or f"backup_{timestamp}"
        backup_path = os.path.join(settings.backup_dir, f"{backup_name}.db")

        # Ensure backup directory exists
        os.makedirs(settings.backup_dir, exist_ok=True)

        # Get current database path
        db_path = settings.database_url.replace("sqlite:///", "") if "sqlite" in settings.database_url else None

        # Create backup
        success = backup_database(backup_path, db_path)

        if success:
            # Get backup file size
            file_size = os.path.getsize(backup_path) if os.path.exists(backup_path) else 0

            logger.info(f"Database backup created: {backup_path}")
            return {
                "message": "Database backup created successfully",
                "backup_path": backup_path,
                "backup_name": backup_name,
                "file_size_bytes": file_size,
                "created_at": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Database backup failed")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database backup failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database backup failed: {str(e)}")

@router.post("/database/restore",
            summary="Restore Database from Backup",
            description="""Restore the application database from a previously created backup file.

            **Restore Process:**
            1. **Backup Validation**: Verifies backup file exists
            2. **Current Database Backup**: Creates safety backup of current database
            3. **Database Replacement**: Replaces current database with backup
            4. **Validation**: Verifies database integrity after restore

            **Safety Considerations:**
            - **Destructive Operation**: Overwrites current database completely
            - **Irreversible**: Cannot undo restore operation
            - **Data Loss**: All changes since backup will be lost
            - **Service Impact**: May require application restart

            **Prerequisites:**
            - Backup file must exist in backup directory
            - Sufficient disk space for restore operation
            - Application should be in maintenance mode if possible
            - Current users should be notified of impending restore

            **Security:**
            - Requires admin privileges
            - Audit logging of restore operations
            - Backup file integrity validation

            **Use Cases:**
            - Disaster recovery from database corruption
            - Rollback to previous state after failed deployment
            - Data recovery from accidental deletion
            - Testing with production data snapshots

            **Warning:**
            - This operation cannot be undone
            - Ensure you have a recent backup before restoring
            - Consider notifying users of potential data loss
            """,
            responses={
                200: {
                    "description": "Database restored successfully",
                    "content": {
                        "application/json": {
                            "example": {
                                "message": "Database restored successfully",
                                "backup_name": "backup_20250115_103000",
                                "restored_at": "2025-01-15T10:30:00"
                            }
                        }
                    }
                },
                403: {
                    "description": "Admin privileges required"
                },
                404: {
                    "description": "Backup file not found"
                },
                500: {
                    "description": "Internal server error during restore"
                }
            })
async def restore_database_backup(
    backup_name: str,
    current_user: User = Depends(get_current_user)
):
    """
    Restore database from backup

    Requires admin privileges
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        backup_path = os.path.join(settings.backup_dir, f"{backup_name}.db")

        if not os.path.exists(backup_path):
            raise HTTPException(status_code=404, detail=f"Backup file not found: {backup_name}")

        # Get current database path
        db_path = settings.database_url.replace("sqlite:///", "") if "sqlite" in settings.database_url else None

        # Restore database
        success = restore_database(backup_path, db_path)

        if success:
            logger.info(f"Database restored from: {backup_path}")
            return {
                "message": "Database restored successfully",
                "backup_name": backup_name,
                "restored_at": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Database restore failed")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database restore failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database restore failed: {str(e)}")

@router.get("/database/backups",
            summary="List Database Backups",
            description="""Retrieve a list of all available database backups with metadata.

            **Backup Information Provided:**
            - **name**: Backup identifier (filename without extension)
            - **filename**: Full backup filename with extension
            - **path**: Complete file system path to backup
            - **size_bytes**: File size in bytes for storage planning
            - **created_at**: Backup creation timestamp
            - **modified_at**: Last modification timestamp

            **Sorting:**
            - Results ordered by creation date (newest first)
            - Easy access to most recent backups
            - Chronological backup history

            **Use Cases:**
            - Browse available backups for restore selection
            - Monitor backup storage usage
            - Verify backup schedule compliance
            - Audit backup history for compliance
            - Plan backup retention and cleanup

            **Storage Management:**
            - Identify old backups for cleanup
            - Monitor total backup storage consumption
            - Validate backup retention policies
            """,
            responses={
                200: {
                    "description": "Database backups listed successfully",
                    "content": {
                        "application/json": {
                            "example": {
                                "backups": [
                                    {
                                        "name": "backup_20250115_103000",
                                        "filename": "backup_20250115_103000.db",
                                        "path": "/backups/backup_20250115_103000.db",
                                        "size_bytes": 2048000,
                                        "created_at": "2025-01-15T10:30:00",
                                        "modified_at": "2025-01-15T10:30:00"
                                    }
                                ]
                            }
                        }
                    }
                },
                403: {
                    "description": "Admin privileges required"
                },
                500: {
                    "description": "Internal server error during backup listing"
                }
            })
async def list_database_backups(current_user: User = Depends(get_current_user)):
    """
    List available database backups

    Requires admin privileges
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        if not os.path.exists(settings.backup_dir):
            return {"backups": []}

        backups = []
        for filename in os.listdir(settings.backup_dir):
            if filename.endswith('.db'):
                filepath = os.path.join(settings.backup_dir, filename)
                stat = os.stat(filepath)

                backups.append({
                    "name": filename.replace('.db', ''),
                    "filename": filename,
                    "path": filepath,
                    "size_bytes": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })

        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x['created_at'], reverse=True)

        return {"backups": backups}

    except Exception as e:
        logger.error(f"Failed to list backups: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list backups: {str(e)}")

@router.delete("/database/backup/{backup_name}",
            summary="Delete Database Backup",
            description="""Permanently delete a database backup file.

            **Deletion Process:**
            1. **Backup Validation**: Verifies backup file exists
            2. **File Deletion**: Removes backup file from filesystem
            3. **Confirmation**: Returns success message

            **Impact:**
            - Backup file permanently removed
            - No recovery possible after deletion
            - Frees up storage space
            - Backup history becomes incomplete

            **Safety Considerations:**
            - Verify backup is no longer needed before deletion
            - Consider retention policy requirements
            - Ensure newer backups exist for recovery
            - Audit trail of deletion for compliance

            **Use Cases:**
            - Implement backup retention policies
            - Free up storage space from old backups
            - Clean up failed or corrupted backups
            - Manage backup lifecycle

            **Warning:**
            - This action cannot be undone
            - Ensure backup is not needed for compliance or recovery
            """,
            responses={
                200: {
                    "description": "Backup deleted successfully",
                    "content": {
                        "application/json": {
                            "example": {
                                "message": "Backup backup_20250115_103000 deleted successfully"
                            }
                        }
                    }
                },
                403: {
                    "description": "Admin privileges required"
                },
                404: {
                    "description": "Backup file not found"
                },
                500: {
                    "description": "Internal server error during backup deletion"
                }
            })
async def delete_database_backup(
    backup_name: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a database backup

    Requires admin privileges
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        backup_path = os.path.join(settings.backup_dir, f"{backup_name}.db")

        if not os.path.exists(backup_path):
            raise HTTPException(status_code=404, detail=f"Backup file not found: {backup_name}")

        os.remove(backup_path)

        logger.info(f"Database backup deleted: {backup_path}")
        return {"message": f"Backup {backup_name} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete backup: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete backup: {str(e)}")

@router.get("/database/health",
            summary="Get Database Health Status",
            description="""Retrieve comprehensive health status information for the application database.

            **Health Metrics Provided:**
            - **database_type**: Type of database (SQLite, PostgreSQL)
            - **connected**: Connection status (true/false)
            - **size**: Database size information
            - **pool_stats**: Connection pool statistics (if applicable)
            - **status**: Overall health status (healthy, degraded, error)
            - **timestamp**: Health check execution time

            **Monitoring Use:**
            - Kubernetes liveness and readiness probes
            - External monitoring systems (Prometheus, Datadog)
            - Health check dashboards
            - Automated alerting on database issues

            **Health Indicators:**
            - Connection availability and responsiveness
            - Database size and growth tracking
            - Connection pool utilization
            - Query performance metrics

            **No Authentication Required:**
            - Allows monitoring systems to check health without credentials
            - Safe endpoint with no sensitive data exposure
            - Rate limiting recommended for production

            **Use Cases:**
            - Infrastructure monitoring and alerting
            - Automated health checks in CI/CD pipelines
            - Load balancer health checks
            - Database performance monitoring
            """,
            responses={
                200: {
                    "description": "Database health status retrieved successfully",
                    "content": {
                        "application/json": {
                            "example": {
                                "database_type": "SQLite",
                                "connected": True,
                                "size": {
                                    "total_bytes": 10240000,
                                    "total_mb": 10.24
                                },
                                "pool_stats": {
                                    "active_connections": 5,
                                    "idle_connections": 10,
                                    "total_connections": 15
                                },
                                "status": "healthy",
                                "timestamp": "2025-01-15T10:30:00"
                            }
                        }
                    }
                },
                500: {
                    "description": "Database health check failed"
                }
            })
async def get_database_health():
    """
    Get database health status (no auth required for monitoring)
    """
    try:
        health_info = check_database_health()

        return {
            "database_type": health_info.get("database_type", "unknown"),
            "connected": health_info.get("database_connected", False),
            "size": health_info.get("database_size", {}),
            "pool_stats": health_info.get("pool_stats", {}),
            "status": health_info.get("status", "unknown"),
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return {
            "connected": False,
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.post("/model/backup",
            summary="Create ML Model Backup",
            description="""Create a backup of machine learning models and related configuration files.

            **Backup Contents:**
            - **Trained Model Files**: LightGBM model (.txt or .pkl format)
            - **Preprocessing Objects**: Scalers, encoders, transformers
            - **Model Manifest**: Model metadata and configuration
            - **Feature Specifications**: Feature names and types

            **Files Backed Up:**
            - settings.model_path: Main trained model file
            - settings.preprocessing_path: Preprocessing pipeline
            - settings.model_manifest_path: Model metadata

            **Storage Location:**
            - {backup_dir}/models/{backup_name}/
            - Preserves original filenames
            - Organized by backup timestamp

            **Use Cases:**
            - Model version control and rollback
            - Pre-deployment model backups
            - Model archival for compliance
            - Disaster recovery for ML models

            **Security:**
            - Requires admin privileges
            - Models may contain sensitive patterns learned from healthcare data
            """,
            responses={
                200: {
                    "description": "Model backup created successfully",
                    "content": {
                        "application/json": {
                            "example": {
                                "message": "Model backup created successfully",
                                "backup_path": "/backups/models/model_backup_20250115_103000",
                                "backup_name": "model_backup_20250115_103000",
                                "files_backed_up": ["model.txt", "preprocessing.pkl", "model_manifest.json"],
                                "created_at": "2025-01-15T10:30:00"
                            }
                        }
                    }
                },
                403: {
                    "description": "Admin privileges required"
                },
                500: {
                    "description": "Internal server error during model backup"
                }
            })
async def create_model_backup(
    background_tasks: BackgroundTasks,
    backup_name: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Create a backup of ML models and related files

    Requires admin privileges
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        import shutil
        from pathlib import Path

        # Generate backup name
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_name = backup_name or f"model_backup_{timestamp}"
        backup_path = os.path.join(settings.backup_dir, "models", backup_name)

        # Ensure backup directory exists
        os.makedirs(backup_path, exist_ok=True)

        # Files to backup
        model_files = [
            settings.model_path,
            settings.preprocessing_path,
            settings.model_manifest_path
        ]

        backed_up_files = []

        for file_path in model_files:
            if file_path and os.path.exists(file_path):
                filename = os.path.basename(file_path)
                dest_path = os.path.join(backup_path, filename)
                shutil.copy2(file_path, dest_path)
                backed_up_files.append(filename)

        logger.info(f"Model backup created: {backup_path}")
        return {
            "message": "Model backup created successfully",
            "backup_path": backup_path,
            "backup_name": backup_name,
            "files_backed_up": backed_up_files,
            "created_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Model backup failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Model backup failed: {str(e)}")

@router.get("/model/backups",
            summary="List ML Model Backups",
            description="""Retrieve a list of all available ML model backups with metadata.

            **Backup Information Provided:**
            - **name**: Backup identifier (directory name)
            - **path**: Complete file system path to backup directory
            - **files**: List of files included in backup
            - **file_count**: Number of files in backup
            - **created_at**: Backup creation timestamp

            **Sorting:**
            - Results ordered by creation date (newest first)
            - Easy access to most recent model backups

            **Use Cases:**
            - Browse available model backups for restore
            - Monitor model backup storage usage
            - Track model version history
            - Verify backup schedule compliance
            """,
            responses={
                200: {
                    "description": "Model backups listed successfully",
                    "content": {
                        "application/json": {
                            "example": {
                                "backups": [
                                    {
                                        "name": "model_backup_20250115_103000",
                                        "path": "/backups/models/model_backup_20250115_103000",
                                        "files": ["model.txt", "preprocessing.pkl", "model_manifest.json"],
                                        "file_count": 3,
                                        "created_at": "2025-01-15T10:30:00"
                                    }
                                ]
                            }
                        }
                    }
                },
                403: {
                    "description": "Admin privileges required"
                },
                500: {
                    "description": "Internal server error during model backup listing"
                }
            })
async def list_model_backups(current_user: User = Depends(get_current_user)):
    """
    List available model backups

    Requires admin privileges
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        models_backup_dir = os.path.join(settings.backup_dir, "models")

        if not os.path.exists(models_backup_dir):
            return {"backups": []}

        backups = []
        for dirname in os.listdir(models_backup_dir):
            dirpath = os.path.join(models_backup_dir, dirname)
            if os.path.isdir(dirpath):
                stat = os.stat(dirpath)
                files = os.listdir(dirpath)

                backups.append({
                    "name": dirname,
                    "path": dirpath,
                    "files": files,
                    "file_count": len(files),
                    "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat()
                })

        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x['created_at'], reverse=True)

        return {"backups": backups}

    except Exception as e:
        logger.error(f"Failed to list model backups: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list model backups: {str(e)}")

@router.post("/full-backup",
            summary="Create Full System Backup",
            description="""Create a comprehensive backup of both the database and ML models.

            **Full Backup Contents:**
            - **Database Backup**: Complete application database with all tables
            - **Model Backup**: Trained models and preprocessing objects
            - **Configuration**: Model manifests and metadata
            - **Integrated Snapshot**: Consistent point-in-time system state

            **Backup Structure:**
            ```
            {backup_dir}/full/{backup_name}/
            ├── {backup_name}_db.db          # Database backup
            └── models/                       # Model files
                ├── model.txt
                ├── preprocessing.pkl
                └── model_manifest.json
            ```

            **Advantages:**
            - **Consistency**: Database and models from same point in time
            - **Complete Recovery**: Single backup for full system restore
            - **Simplified Management**: One backup vs multiple separate backups

            **Use Cases:**
            - Complete system snapshots for disaster recovery
            - Pre-deployment backups before major releases
            - Compliance requirements for data + model backups
            - System migration and replication
            """,
            responses={
                200: {
                    "description": "Full system backup created successfully",
                    "content": {
                        "application/json": {
                            "example": {
                                "message": "Full system backup created successfully",
                                "backup_path": "/backups/full/full_backup_20250115_103000",
                                "backup_name": "full_backup_20250115_103000",
                                "database_backup": {
                                    "path": "/backups/full/full_backup_20250115_103000/full_backup_20250115_103000_db.db",
                                    "size_bytes": 2048000
                                },
                                "model_backup": {
                                    "path": "/backups/full/full_backup_20250115_103000/models",
                                    "files": ["model.txt", "preprocessing.pkl", "model_manifest.json"]
                                },
                                "created_at": "2025-01-15T10:30:00"
                            }
                        }
                    }
                },
                403: {
                    "description": "Admin privileges required"
                },
                500: {
                    "description": "Internal server error during full backup creation"
                }
            })
async def create_full_backup(
    background_tasks: BackgroundTasks,
    backup_name: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Create a full system backup (database + models)

    Requires admin privileges
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        # Generate backup name
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_name = backup_name or f"full_backup_{timestamp}"
        backup_path = os.path.join(settings.backup_dir, "full", backup_name)

        # Ensure backup directory exists
        os.makedirs(backup_path, exist_ok=True)

        results = {
            "database_backup": None,
            "model_backup": None
        }

        # Database backup
        db_backup_name = f"{backup_name}_db"
        db_backup_path = os.path.join(backup_path, f"{db_backup_name}.db")
        db_path = settings.database_url.replace("sqlite:///", "") if "sqlite" in settings.database_url else None

        if backup_database(db_backup_path, db_path):
            results["database_backup"] = {
                "path": db_backup_path,
                "size_bytes": os.path.getsize(db_backup_path) if os.path.exists(db_backup_path) else 0
            }

        # Model backup
        import shutil
        model_backup_path = os.path.join(backup_path, "models")
        os.makedirs(model_backup_path, exist_ok=True)

        model_files = [
            settings.model_path,
            settings.preprocessing_path,
            settings.model_manifest_path
        ]

        backed_up_files = []
        for file_path in model_files:
            if file_path and os.path.exists(file_path):
                filename = os.path.basename(file_path)
                dest_path = os.path.join(model_backup_path, filename)
                shutil.copy2(file_path, dest_path)
                backed_up_files.append(filename)

        results["model_backup"] = {
            "path": model_backup_path,
            "files": backed_up_files
        }

        logger.info(f"Full system backup created: {backup_path}")
        return {
            "message": "Full system backup created successfully",
            "backup_path": backup_path,
            "backup_name": backup_name,
            "database_backup": results["database_backup"],
            "model_backup": results["model_backup"],
            "created_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Full backup failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Full backup failed: {str(e)}")
