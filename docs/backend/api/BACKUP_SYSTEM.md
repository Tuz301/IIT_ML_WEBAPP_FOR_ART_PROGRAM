# Automated Backup System Documentation

## Overview

The IIT ML Service includes a comprehensive automated backup system that protects critical data including databases, ML models, configuration files, and logs. The system supports scheduled backups, manual backups, encryption, integrity verification, and automated cleanup.

## Table of Contents

1. [Architecture](#architecture)
2. [Backup Types](#backup-types)
3. [Directory Structure](#directory-structure)
4. [Configuration](#configuration)
5. [Scheduled Backups](#scheduled-backups)
6. [Manual Backups](#manual-backups)
7. [Restoring Backups](#restoring-backups)
8. [Backup Verification](#backup-verification)
9. [Monitoring & Alerts](#monitoring--alerts)
10. [Troubleshooting](#troubleshooting)

---

## Architecture

### Components

```
backup_system/
├── backup_scheduler.py    # Automated scheduling and execution
├── restore_database.py    # Database restore CLI tool
└── backup.py              # Core backup/restore logic
```

### Data Flow

```
┌─────────────────┐
│ Backup Scheduler│
│   (Periodic)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────┐
│ Backup Manager  │────▶│ Encryption   │
└────────┬────────┘     └──────────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────┐
│   Components    │────▶│ Compression  │
│ - Database      │     └──────────────┘
│ - Models        │
│ - Config        │
│ - Logs          │
└─────────────────┘
```

---

## Backup Types

### Full Backup

A complete backup of all selected components:
- Database dump
- ML model files
- Configuration files
- Log files (optional)

**Usage:** Daily or weekly for complete system snapshots

**Example:**
```python
from app.utils.backup import backup_manager

metadata = backup_manager.create_full_backup(
    components=["database", "models", "config"]
)
print(f"Backup ID: {metadata.backup_id}")
print(f"Size: {metadata.size_bytes} bytes")
```

### Incremental Backup

Backup of changes since the last full backup:
- Database changes
- Model updates
- Modified configuration

**Usage:** Hourly or daily for frequent data protection

**Example:**
```python
metadata = backup_manager.create_incremental_backup()
print(f"Incremental backup: {metadata.backup_id}")
```

---

## Directory Structure

```
backups/
├── full/                    # Full system backups
│   ├── full_20240101_020000.tar.gz
│   ├── full_20240101_020000.metadata.json
│   └── full_20240102_020000.tar.gz
├── incremental/             # Incremental backups
│   ├── incr_20240101_080000.tar.gz
│   └── incr_20240101_120000.tar.gz
├── config/                  # Configuration-only backups
├── models/                  # Model-only backups
├── temp/                    # Temporary working directory
└── schedules.json           # Schedule configuration
```

### Backup Metadata Format

```json
{
  "backup_id": "full_20240101_020000",
  "timestamp": "2024-01-01T02:00:00",
  "version": "1.0.0",
  "type": "full",
  "size_bytes": 104857600,
  "checksum": "a1b2c3d4e5f6...",
  "components": ["database", "models", "config"],
  "status": "success"
}
```

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BACKUP_DIR` | Backup storage directory | `./backups` |
| `BACKUP_RETENTION_DAYS` | Days to keep backups | `30` |
| `BACKUP_COMPRESSION_LEVEL` | Gzip compression (0-9) | `9` |
| `BACKUP_MAX_SIZE_GB` | Maximum backup size | `10.0` |
| `BACKUP_ENCRYPT` | Encrypt backups | `true` |
| `NOTIFICATION_EMAIL` | Email for alerts | - |
| `SMTP_SERVER` | SMTP server for notifications | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP port | `587` |
| `SMTP_USERNAME` | SMTP username | - |
| `SMTP_PASSWORD` | SMTP password | - |

### BackupConfig Class

```python
@dataclass
class BackupConfig:
    retention_days: int = 30
    compression_level: int = 9
    max_backup_size_gb: float = 10.0
    include_models: bool = True
    include_config: bool = True
    include_logs: bool = False
    encrypt_backups: bool = True
    backup_schedule: str = "daily"
```

---

## Scheduled Backups

### Schedule Types

| Type | Description | Default Time |
|------|-------------|--------------|
| `daily` | Run once per day | 2:00 AM UTC |
| `weekly` | Run once per week | Sunday 2:00 AM UTC |
| `monthly` | Run once per month | 1st of month 2:00 AM UTC |

### Creating a Schedule

```python
from app.utils.backup import backup_scheduler

schedule_config = {
    "schedule_type": "daily",
    "components": ["database", "models", "config"],
    "retention_days": 30,
    "include_models": True,
    "include_config": True,
    "include_logs": False,
    "notification_email": "admin@example.com"
}

schedule_id = backup_scheduler.schedule_backup(schedule_config)
print(f"Schedule ID: {schedule_id}")
```

### Running the Scheduler

```bash
# Start the backup scheduler
python -m backend.ml-service.scripts.backup_scheduler
```

The scheduler runs continuously, checking every 5 minutes for due backups.

### Schedule Management

```python
# List all schedules
print(backup_scheduler.schedules)

# Remove a schedule
backup_scheduler.remove_schedule(schedule_id)

# Get due schedules
due = backup_scheduler.get_due_schedules()
```

### Schedule File Format

```json
{
  "schedule_id": "uuid-here",
  "schedule_type": "daily",
  "components": ["database", "models", "config"],
  "retention_days": 30,
  "next_run": "2024-01-02T02:00:00",
  "status": "active",
  "created_at": "2024-01-01T00:00:00",
  "last_run": "2024-01-01T02:00:00",
  "last_status": "success",
  "consecutive_failures": 0
}
```

---

## Manual Backups

### Create Full Backup

```python
from app.utils.backup import backup_manager

# Backup all components
metadata = backup_manager.create_full_backup()

# Backup specific components
metadata = backup_manager.create_full_backup(
    components=["database", "config"]
)
```

### Create Incremental Backup

```python
# Incremental since last full backup
metadata = backup_manager.create_incremental_backup()

# Incremental since specific backup
metadata = backup_manager.create_incremental_backup(
    since_backup_id="full_20240101_020000"
)
```

### List Available Backups

```python
# List all backups
all_backups = backup_manager.list_backups()

# List only full backups
full_backups = backup_manager.list_backups("full")

# List only incremental backups
incr_backups = backup_manager.list_backups("incremental")

for backup in all_backups:
    print(f"{backup.backup_id} - {backup.timestamp} - {backup.size_bytes} bytes")
```

---

## Restoring Backups

### Using the Restore Script

```bash
# Restore from backup file (interactive - requires confirmation)
python backend/ml-service/scripts/restore_database.py backups/full/full_20240101_020000.tar.gz

# Restore with confirmation flag
python backend/ml-service/scripts/restore_database.py backups/full/full_20240101_020000.tar.gz --confirm

# Restore and create database if it doesn't exist
python backend/ml-service/scripts/restore_database.py backups/full/full_20240101_020000.tar.gz --confirm --create-db
```

### Using Python API

```python
from app.utils.backup import backup_manager

# Restore all components from backup
success = backup_manager.restore_from_backup("full_20240101_020000")

# Restore specific components only
success = backup_manager.restore_from_backup(
    "full_20240101_020000",
    components=["database"]
)
```

### Restore Process

1. **Validation** - Verify backup exists and integrity is intact
2. **Decryption** - Decrypt if backup is encrypted
3. **Extraction** - Extract archive to temporary directory
4. **Component Restoration** - Restore each selected component
5. **Cleanup** - Remove temporary files

### Safety Features

- `--confirm` flag required for destructive operations
- Backup integrity verification before restore
- Automatic rollback on failure
- Detailed logging of restore operations

---

## Backup Verification

### Integrity Check

```python
from app.utils.backup import backup_manager

# Verify backup integrity using checksum
is_valid = backup_manager.verify_backup_integrity("full_20240101_020000")

if is_valid:
    print("Backup is valid and intact")
else:
    print("Backup is corrupted or missing")
```

### Manual Verification

```bash
# Check backup file exists
ls -lh backups/full/full_20240101_020000.tar.gz

# Verify checksum
sha256sum backups/full/full_20240101_020000.tar.gz

# Compare with metadata checksum
cat backups/full/full_20240101_020000.metadata.json | grep checksum
```

---

## Monitoring & Alerts

### Email Notifications

The backup scheduler sends email notifications for:
- ✅ Successful backup completion
- ❌ Backup failures
- ⚠️ Schedule disabled (too many failures)

**Notification Format:**
```
Subject: IIT ML Service - Backup Success: schedule-id

Scheduled backup schedule-id completed successfully.
Backup ID: full_20240101_020000
Size: 104857600 bytes
Next run: 2024-01-02T02:00:00
```

### Monitoring Metrics

Track these metrics for backup health:

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| Backup Success Rate | % of successful backups | < 95% |
| Backup Duration | Time to complete backup | > 30 minutes |
| Backup Size | Size of backup files | > 5 GB |
| Consecutive Failures | Failed backups in a row | ≥ 3 |
| Retention Compliance | Backups within retention | < 90% |

### Prometheus Integration

```python
from prometheus_client import Counter, Histogram, Gauge

backup_success = Counter('backup_success_total', 'Total successful backups')
backup_failure = Counter('backup_failure_total', 'Total failed backups')
backup_duration = Histogram('backup_duration_seconds', 'Backup duration')
backup_size = Gauge('backup_size_bytes', 'Current backup size')
```

---

## Troubleshooting

### Common Issues

#### 1. Backup Fails with "Database backup failed"

**Cause:** Database connection issues or insufficient permissions

**Solution:**
```bash
# Check database connection
python -c "from app.core.db import engine; print(engine.connect())"

# Check database file permissions
ls -la iit_ml_service.db

# Ensure database is not locked
# Stop the application before backup
```

#### 2. Encryption/Decryption Fails

**Cause:** Encryption key mismatch or corrupted data

**Solution:**
```bash
# Check encryption key is set
echo $ENCRYPTION_KEY

# Verify backup file is not corrupted
sha256sum backups/full/full_20240101_020000.tar.gz.enc
```

#### 3. Scheduler Not Running

**Cause:** Process crashed or not started

**Solution:**
```bash
# Check if scheduler is running
ps aux | grep backup_scheduler

# Check scheduler logs
tail -f logs/backup_scheduler.log

# Restart scheduler
python -m backend.ml-service.scripts.backup_scheduler
```

#### 4. Disk Space Issues

**Cause:** Insufficient disk space for backups

**Solution:**
```bash
# Check disk space
df -h

# Clean up old backups manually
python -c "from app.utils.backup import backup_manager; print(backup_manager.cleanup_old_backups())"

# Reduce retention period
export BACKUP_RETENTION_DAYS=7
```

#### 5. Email Notifications Not Received

**Cause:** SMTP configuration issues

**Solution:**
```bash
# Verify SMTP credentials
echo $SMTP_USERNAME
echo $SMTP_PASSWORD

# Test SMTP connection
python -c "
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('your@email.com', 'your-password')
print('SMTP connection successful')
"
```

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Or via environment:
```bash
export LOG_LEVEL=DEBUG
python -m backend.ml-service.scripts.backup_scheduler
```

### Recovery Procedures

#### Scenario: Corrupted Latest Backup

1. Identify the last valid backup:
```python
backups = backup_manager.list_backups()
for backup in backups:
    if backup_manager.verify_backup_integrity(backup.backup_id):
        print(f"Valid backup: {backup.backup_id}")
        break
```

2. Restore from valid backup:
```bash
python backend/ml-service/scripts/restore_database.py backups/full/full_20240101_020000.tar.gz --confirm
```

#### Scenario: Lost Encryption Key

1. Decrypt using manual key:
```python
from app.utils.encryption import encryption
# Manually provide key
encryption.key = b'manual-key-here'
```

2. Or restore from unencrypted backup if available

---

## Best Practices

1. **Regular Testing**: Test restore procedures monthly
2. **Offsite Storage**: Copy backups to cloud storage (S3, GCS, Azure)
3. **Multiple Schedules**: Use both full and incremental backups
4. **Monitoring**: Set up alerts for backup failures
5. **Documentation**: Document any custom backup procedures
6. **Encryption**: Always encrypt backups containing sensitive data
7. **Retention**: Keep backups for at least 30 days
8. **Verification**: Verify backup integrity regularly
9. **Capacity Planning**: Monitor disk space and backup growth
10. **Disaster Recovery**: Have a documented DR plan

---

## API Reference

### BackupManager

| Method | Description |
|--------|-------------|
| `create_full_backup(components)` | Create full system backup |
| `create_incremental_backup(since_backup_id)` | Create incremental backup |
| `restore_from_backup(backup_id, components)` | Restore from backup |
| `list_backups(backup_type)` | List available backups |
| `cleanup_old_backups()` | Remove old backups |
| `verify_backup_integrity(backup_id)` | Verify backup checksum |

### BackupScheduler

| Method | Description |
|--------|-------------|
| `schedule_backup(schedule_config)` | Create new schedule |
| `remove_schedule(schedule_id)` | Remove schedule |
| `get_due_schedules()` | Get schedules due for execution |
| `execute_scheduled_backup(schedule)` | Execute scheduled backup |
| `run_scheduler()` | Main scheduler loop |

---

## Support

For issues or questions about the backup system:
- Check logs: `logs/backup_scheduler.log`
- Review this documentation
- Contact system administrator
