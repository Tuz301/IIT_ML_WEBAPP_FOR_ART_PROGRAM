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

@router.post("/database/backup")
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

@router.post("/database/restore")
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

@router.get("/database/backups")
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

@router.delete("/database/backup/{backup_name}")
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

@router.get("/database/health")
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

@router.post("/model/backup")
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

@router.get("/model/backups")
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

@router.post("/full-backup")
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
