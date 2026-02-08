#!/usr/bin/env python3
"""
Database restore script for IIT ML Service
"""
import os
import sys
import argparse
import logging
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.db import restore_database_backup, DATABASE_URL

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description='Restore IIT ML Service database')
    parser.add_argument(
        'backup_file',
        help='Path to the backup file to restore'
    )
    parser.add_argument(
        '--confirm',
        action='store_true',
        help='Confirm restore operation (required for safety)'
    )
    parser.add_argument(
        '--create-db',
        action='store_true',
        help='Create database if it does not exist'
    )

    args = parser.parse_args()

    backup_path = Path(args.backup_file)

    # Validate backup file exists
    if not backup_path.exists():
        logger.error(f"❌ Backup file not found: {backup_path}")
        return 1

    # Safety check - require confirmation
    if not args.confirm:
        logger.warning("⚠️  WARNING: Database restore will overwrite existing data!")
        logger.warning("This operation cannot be undone.")
        logger.warning("")
        logger.warning("To proceed, run with --confirm flag:")
        logger.warning(f"    python {sys.argv[0]} {args.backup_file} --confirm")
        return 1

    logger.info(f"Starting database restore from: {backup_path}")
    logger.info(f"Database URL: {DATABASE_URL.replace(DATABASE_URL.split('@')[0].split('//')[1].split(':')[1], '***')}")

    # Show backup file info
    file_size = backup_path.stat().st_size
    logger.info(f"📁 Backup file: {backup_path}")
    logger.info(f"📊 File size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")

    try:
        success = restore_database_backup(str(backup_path))

        if success:
            logger.info("✅ Database restore completed successfully!")
            logger.info("🔄 You may need to restart the application to ensure all connections use the restored data.")
            return 0
        else:
            logger.error("❌ Database restore failed!")
            return 1

    except KeyboardInterrupt:
        logger.info("Restore interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error during restore: {str(e)}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
