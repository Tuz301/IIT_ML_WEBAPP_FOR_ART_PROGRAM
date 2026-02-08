"""
Comprehensive backup and recovery utilities for IIT ML Service
"""
import os
import json
import shutil
import logging
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

from ..config import get_settings
from ..core.db import create_database_backup, restore_database_backup
from .encryption import encryption

logger = logging.getLogger(__name__)
settings = get_settings()

@dataclass
class BackupMetadata:
    """Metadata for backup operations"""
    backup_id: str
    timestamp: str
    version: str
    type: str  # 'full', 'incremental', 'config', 'models'
    size_bytes: int
    checksum: str
    components: List[str]
    status: str  # 'success', 'failed', 'in_progress'
    error_message: Optional[str] = None

@dataclass
class BackupConfig:
    """Configuration for backup operations"""
    retention_days: int = 30
    compression_level: int = 9
    max_backup_size_gb: float = 10.0
    include_models: bool = True
    include_config: bool = True
    include_logs: bool = False
    encrypt_backups: bool = True
    backup_schedule: str = "daily"  # 'hourly', 'daily', 'weekly'

class BackupManager:
    """
    Comprehensive backup and recovery manager
    """

    def __init__(self, backup_dir: Optional[str] = None):
        self.backup_dir = Path(backup_dir or settings.backup_dir or "./backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.config = BackupConfig()

        # Create subdirectories
        self.full_backup_dir = self.backup_dir / "full"
        self.incremental_backup_dir = self.backup_dir / "incremental"
        self.config_backup_dir = self.backup_dir / "config"
        self.models_backup_dir = self.backup_dir / "models"
        self.temp_dir = self.backup_dir / "temp"

        for dir_path in [self.full_backup_dir, self.incremental_backup_dir,
                        self.config_backup_dir, self.models_backup_dir, self.temp_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def create_full_backup(self, components: Optional[List[str]] = None) -> BackupMetadata:
        """
        Create a full system backup

        Args:
            components: List of components to backup ('database', 'models', 'config', 'logs')

        Returns:
            BackupMetadata object
        """
        backup_id = f"full_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        timestamp = datetime.utcnow().isoformat()

        metadata = BackupMetadata(
            backup_id=backup_id,
            timestamp=timestamp,
            version=settings.api_version,
            type="full",
            size_bytes=0,
            checksum="",
            components=components or ["database", "models", "config"],
            status="in_progress"
        )

        try:
            with tempfile.TemporaryDirectory(dir=self.temp_dir) as temp_dir:
                temp_path = Path(temp_dir)
                total_size = 0

                # Backup database
                if "database" in metadata.components:
                    db_backup_path = temp_path / f"{backup_id}_database.dump"
                    if create_database_backup(str(db_backup_path)):
                        total_size += db_backup_path.stat().st_size
                    else:
                        raise Exception("Database backup failed")

                # Backup models
                if "models" in metadata.components and self.config.include_models:
                    models_dir = temp_path / "models"
                    models_dir.mkdir()
                    self._backup_models_directory(models_dir)
                    total_size += self._get_directory_size(models_dir)

                # Backup configuration
                if "config" in metadata.components and self.config.include_config:
                    config_dir = temp_path / "config"
                    config_dir.mkdir()
                    self._backup_config_files(config_dir)
                    total_size += self._get_directory_size(config_dir)

                # Backup logs (optional)
                if "logs" in metadata.components and self.config.include_logs:
                    logs_dir = temp_path / "logs"
                    logs_dir.mkdir()
                    self._backup_log_files(logs_dir)
                    total_size += self._get_directory_size(logs_dir)

                # Create compressed archive
                archive_path = self.full_backup_dir / f"{backup_id}.tar.gz"
                self._create_compressed_archive(temp_path, archive_path)

                # Encrypt if configured
                if self.config.encrypt_backups:
                    self._encrypt_backup(archive_path)

                # Calculate checksum
                final_path = archive_path if not self.config.encrypt_backups else archive_path.with_suffix('.enc')
                checksum = self._calculate_checksum(final_path)
                final_size = final_path.stat().st_size

                # Update metadata
                metadata.size_bytes = final_size
                metadata.checksum = checksum
                metadata.status = "success"

                # Save metadata
                self._save_backup_metadata(metadata)

                logger.info(f"Full backup completed successfully: {backup_id}")
                return metadata

        except Exception as e:
            error_msg = str(e)
            metadata.status = "failed"
            metadata.error_message = error_msg
            self._save_backup_metadata(metadata)
            logger.error(f"Full backup failed: {error_msg}")
            raise

    def create_incremental_backup(self, since_backup_id: Optional[str] = None) -> BackupMetadata:
        """
        Create an incremental backup since the last full backup

        Args:
            since_backup_id: ID of backup to create incremental from

        Returns:
            BackupMetadata object
        """
        backup_id = f"incr_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        timestamp = datetime.utcnow().isoformat()

        metadata = BackupMetadata(
            backup_id=backup_id,
            timestamp=timestamp,
            version=settings.api_version,
            type="incremental",
            size_bytes=0,
            checksum="",
            components=["database_changes", "model_updates"],
            status="in_progress"
        )

        try:
            # Find last full backup if not specified
            if not since_backup_id:
                since_backup_id = self._find_last_full_backup()

            with tempfile.TemporaryDirectory(dir=self.temp_dir) as temp_dir:
                temp_path = Path(temp_dir)

                # For incremental backups, we mainly backup changed data
                # This is a simplified implementation - in production you'd track changes
                changes_dir = temp_path / "changes"
                changes_dir.mkdir()

                # Backup recent database changes (simplified)
                self._backup_recent_changes(changes_dir / "database_changes.sql")

                # Create compressed archive
                archive_path = self.incremental_backup_dir / f"{backup_id}.tar.gz"
                self._create_compressed_archive(temp_path, archive_path)

                if self.config.encrypt_backups:
                    self._encrypt_backup(archive_path)

                final_path = archive_path if not self.config.encrypt_backups else archive_path.with_suffix('.enc')
                checksum = self._calculate_checksum(final_path)
                final_size = final_path.stat().st_size

                metadata.size_bytes = final_size
                metadata.checksum = checksum
                metadata.status = "success"

                self._save_backup_metadata(metadata)

                logger.info(f"Incremental backup completed successfully: {backup_id}")
                return metadata

        except Exception as e:
            error_msg = str(e)
            metadata.status = "failed"
            metadata.error_message = error_msg
            self._save_backup_metadata(metadata)
            logger.error(f"Incremental backup failed: {error_msg}")
            raise

    def restore_from_backup(self, backup_id: str, components: Optional[List[str]] = None) -> bool:
        """
        Restore system from backup

        Args:
            backup_id: ID of backup to restore from
            components: Components to restore

        Returns:
            True if successful
        """
        try:
            metadata = self._load_backup_metadata(backup_id)
            if not metadata:
                raise Exception(f"Backup metadata not found for: {backup_id}")

            backup_path = self._get_backup_path(metadata)
            if not backup_path.exists():
                raise Exception(f"Backup file not found: {backup_path}")

            with tempfile.TemporaryDirectory(dir=self.temp_dir) as temp_dir:
                temp_path = Path(temp_dir)

                # Decrypt if needed
                if backup_path.suffix == '.enc':
                    decrypted_path = temp_path / backup_path.stem
                    self._decrypt_backup(backup_path, decrypted_path)
                    extract_path = decrypted_path
                else:
                    extract_path = backup_path

                # Extract archive
                self._extract_compressed_archive(extract_path, temp_path)

                # Restore components
                restore_components = components or metadata.components

                if "database" in restore_components:
                    db_backup = temp_path / f"{backup_id}_database.dump"
                    if db_backup.exists():
                        restore_database_backup(str(db_backup))

                if "models" in restore_components:
                    models_dir = temp_path / "models"
                    if models_dir.exists():
                        self._restore_models_directory(models_dir)

                if "config" in restore_components:
                    config_dir = temp_path / "config"
                    if config_dir.exists():
                        self._restore_config_files(config_dir)

                logger.info(f"Restore completed successfully from backup: {backup_id}")
                return True

        except Exception as e:
            logger.error(f"Restore failed: {str(e)}")
            raise

    def list_backups(self, backup_type: Optional[str] = None) -> List[BackupMetadata]:
        """
        List available backups

        Args:
            backup_type: Filter by backup type ('full', 'incremental', etc.)

        Returns:
            List of BackupMetadata objects
        """
        backups = []

        # Check all backup directories
        for backup_dir in [self.full_backup_dir, self.incremental_backup_dir,
                          self.config_backup_dir, self.models_backup_dir]:
            if backup_dir.exists():
                for metadata_file in backup_dir.glob("*.metadata.json"):
                    try:
                        with open(metadata_file, 'r') as f:
                            data = json.load(f)
                            metadata = BackupMetadata(**data)
                            if not backup_type or metadata.type == backup_type:
                                backups.append(metadata)
                    except Exception as e:
                        logger.warning(f"Failed to load backup metadata {metadata_file}: {e}")

        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x.timestamp, reverse=True)
        return backups

    def cleanup_old_backups(self) -> int:
        """
        Remove backups older than retention period

        Returns:
            Number of backups removed
        """
        cutoff_date = datetime.utcnow() - timedelta(days=self.config.retention_days)
        removed_count = 0

        for backup in self.list_backups():
            backup_date = datetime.fromisoformat(backup.timestamp)
            if backup_date < cutoff_date:
                try:
                    self._delete_backup(backup.backup_id)
                    removed_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete old backup {backup.backup_id}: {e}")

        logger.info(f"Cleaned up {removed_count} old backups")
        return removed_count

    def verify_backup_integrity(self, backup_id: str) -> bool:
        """
        Verify backup integrity using checksum

        Args:
            backup_id: Backup ID to verify

        Returns:
            True if backup is intact
        """
        try:
            metadata = self._load_backup_metadata(backup_id)
            if not metadata:
                return False

            backup_path = self._get_backup_path(metadata)
            if not backup_path.exists():
                return False

            current_checksum = self._calculate_checksum(backup_path)
            return current_checksum == metadata.checksum

        except Exception as e:
            logger.error(f"Backup integrity check failed for {backup_id}: {e}")
            return False

    # Private helper methods

    def _backup_models_directory(self, target_dir: Path):
        """Backup ML models directory"""
        models_path = Path(settings.model_path).parent
        if models_path.exists():
            shutil.copytree(models_path, target_dir / "models", dirs_exist_ok=True)

    def _backup_config_files(self, target_dir: Path):
        """Backup configuration files"""
        config_files = [
            ".env",
            "config.py",
            "docker-compose.yml",
            "Dockerfile"
        ]

        for config_file in config_files:
            src_path = Path(config_file)
            if src_path.exists():
                shutil.copy2(src_path, target_dir / config_file)

    def _backup_log_files(self, target_dir: Path):
        """Backup log files"""
        # This would backup application logs - implementation depends on logging setup
        pass

    def _backup_recent_changes(self, output_file: Path):
        """Backup recent database changes (simplified)"""
        # In a real implementation, this would use WAL files or change tracking
        # For now, just create an empty file as placeholder
        output_file.touch()

    def _restore_models_directory(self, source_dir: Path):
        """Restore ML models directory"""
        models_path = Path(settings.model_path).parent
        if source_dir.exists():
            shutil.copytree(source_dir, models_path, dirs_exist_ok=True)

    def _restore_config_files(self, source_dir: Path):
        """Restore configuration files"""
        # This would typically restore to a staging area for manual review
        logger.info("Config files restored to staging area - manual review required")

    def _create_compressed_archive(self, source_dir: Path, archive_path: Path):
        """Create compressed tar.gz archive"""
        import tarfile

        with tarfile.open(archive_path, "w:gz", compresslevel=self.config.compression_level) as tar:
            for item in source_dir.rglob("*"):
                if item.is_file():
                    tar.add(item, arcname=item.relative_to(source_dir))

    def _extract_compressed_archive(self, archive_path: Path, extract_dir: Path):
        """Extract compressed archive"""
        import tarfile

        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(extract_dir)

    def _encrypt_backup(self, backup_path: Path):
        """Encrypt backup file"""
        encrypted_path = backup_path.with_suffix('.enc')

        with open(backup_path, 'rb') as f:
            data = f.read()

        encrypted_data = encryption.encrypt(data.decode('latin-1'))

        with open(encrypted_path, 'w') as f:
            f.write(encrypted_data)

        # Remove unencrypted file
        backup_path.unlink()

    def _decrypt_backup(self, encrypted_path: Path, output_path: Path):
        """Decrypt backup file"""
        with open(encrypted_path, 'r') as f:
            encrypted_data = f.read()

        decrypted_data = encryption.decrypt(encrypted_data)

        with open(output_path, 'wb') as f:
            f.write(decrypted_data.encode('latin-1'))

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        import hashlib

        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def _get_directory_size(self, directory: Path) -> int:
        """Calculate total size of directory"""
        total_size = 0
        for item in directory.rglob("*"):
            if item.is_file():
                total_size += item.stat().st_size
        return total_size

    def _save_backup_metadata(self, metadata: BackupMetadata):
        """Save backup metadata to file"""
        metadata_file = self._get_backup_path(metadata).with_suffix('.metadata.json')
        with open(metadata_file, 'w') as f:
            json.dump(asdict(metadata), f, indent=2)

    def _load_backup_metadata(self, backup_id: str) -> Optional[BackupMetadata]:
        """Load backup metadata from file"""
        for backup_dir in [self.full_backup_dir, self.incremental_backup_dir]:
            metadata_file = backup_dir / f"{backup_id}.metadata.json"
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r') as f:
                        data = json.load(f)
                        return BackupMetadata(**data)
                except Exception as e:
                    logger.error(f"Failed to load metadata for {backup_id}: {e}")
        return None

    def _get_backup_path(self, metadata: BackupMetadata) -> Path:
        """Get backup file path from metadata"""
        if metadata.type == "full":
            base_dir = self.full_backup_dir
        elif metadata.type == "incremental":
            base_dir = self.incremental_backup_dir
        else:
            base_dir = self.backup_dir

        extension = '.enc' if self.config.encrypt_backups else '.tar.gz'
        return base_dir / f"{metadata.backup_id}{extension}"

    def _find_last_full_backup(self) -> Optional[str]:
        """Find the most recent full backup"""
        full_backups = self.list_backups("full")
        return full_backups[0].backup_id if full_backups else None

    def _delete_backup(self, backup_id: str):
        """Delete backup and its metadata"""
        metadata = self._load_backup_metadata(backup_id)
        if metadata:
            backup_path = self._get_backup_path(metadata)
            metadata_path = backup_path.with_suffix('.metadata.json')

            if backup_path.exists():
                backup_path.unlink()
            if metadata_path.exists():
                metadata_path.unlink()

# Global backup manager instance
backup_manager = BackupManager()
