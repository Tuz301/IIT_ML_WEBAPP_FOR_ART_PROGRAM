#!/usr/bin/env python3
"""
Automated backup scheduler for IIT ML Service
Handles scheduled backup execution and monitoring
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from ..app.config import get_settings
from ..app.utils.backup import backup_manager
from ..app.core.db import get_db_session

logger = logging.getLogger(__name__)
settings = get_settings()

class BackupScheduler:
    """
    Automated backup scheduler with monitoring and alerting
    """

    def __init__(self):
        self.schedules_file = os.path.join(settings.backup_dir, "schedules.json")
        self.notification_email = settings.notification_email
        self.smtp_server = getattr(settings, 'smtp_server', 'smtp.gmail.com')
        self.smtp_port = getattr(settings, 'smtp_port', 587)
        self.smtp_username = getattr(settings, 'smtp_username', '')
        self.smtp_password = getattr(settings, 'smtp_password', '')

        # Load existing schedules
        self.schedules = self._load_schedules()

    def _load_schedules(self) -> Dict:
        """Load backup schedules from file"""
        if os.path.exists(self.schedules_file):
            try:
                with open(self.schedules_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load schedules: {e}")
        return {}

    def _save_schedules(self):
        """Save backup schedules to file"""
        try:
            os.makedirs(os.path.dirname(self.schedules_file), exist_ok=True)
            with open(self.schedules_file, 'w') as f:
                json.dump(self.schedules, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save schedules: {e}")

    def schedule_backup(self, schedule_config: Dict) -> str:
        """
        Schedule a new automated backup

        Args:
            schedule_config: Configuration dict with keys:
                - schedule_type: 'daily', 'weekly', 'monthly'
                - components: List of components to backup
                - retention_days: Days to retain backups
                - include_models: Whether to include ML models
                - include_config: Whether to include config files
                - include_logs: Whether to include log files
                - notification_email: Email for notifications

        Returns:
            Schedule ID
        """
        import uuid
        schedule_id = str(uuid.uuid4())

        # Calculate next run time
        now = datetime.utcnow()
        if schedule_config['schedule_type'] == 'daily':
            next_run = now.replace(hour=2, minute=0, second=0, microsecond=0) + timedelta(days=1)
        elif schedule_config['schedule_type'] == 'weekly':
            next_run = now.replace(hour=2, minute=0, second=0, microsecond=0) + timedelta(days=(7 - now.weekday()))
        elif schedule_config['schedule_type'] == 'monthly':
            next_run = (now.replace(day=1) + timedelta(days=32)).replace(day=1, hour=2, minute=0, second=0, microsecond=0)
        else:
            raise ValueError(f"Invalid schedule type: {schedule_config['schedule_type']}")

        self.schedules[schedule_id] = {
            **schedule_config,
            'schedule_id': schedule_id,
            'next_run': next_run.isoformat(),
            'status': 'active',
            'created_at': now.isoformat(),
            'last_run': None,
            'last_status': None,
            'consecutive_failures': 0
        }

        self._save_schedules()
        logger.info(f"Scheduled backup {schedule_id} for {schedule_config['schedule_type']} execution")
        return schedule_id

    def remove_schedule(self, schedule_id: str):
        """Remove a backup schedule"""
        if schedule_id in self.schedules:
            del self.schedules[schedule_id]
            self._save_schedules()
            logger.info(f"Removed backup schedule {schedule_id}")

    def get_due_schedules(self) -> List[Dict]:
        """Get schedules that are due for execution"""
        now = datetime.utcnow()
        due_schedules = []

        for schedule_id, schedule in self.schedules.items():
            if schedule['status'] != 'active':
                continue

            next_run = datetime.fromisoformat(schedule['next_run'])
            if next_run <= now:
                due_schedules.append(schedule)

        return due_schedules

    async def execute_scheduled_backup(self, schedule: Dict):
        """Execute a scheduled backup"""
        schedule_id = schedule['schedule_id']
        logger.info(f"Executing scheduled backup {schedule_id}")

        try:
            # Create backup
            components = schedule.get('components', ['database', 'models', 'config'])
            if 'database' in components:
                backup_metadata = backup_manager.create_database_backup()
            else:
                backup_metadata = backup_manager.create_full_backup(components)

            # Update schedule status
            schedule['last_run'] = datetime.utcnow().isoformat()
            schedule['last_status'] = 'success'
            schedule['consecutive_failures'] = 0

            # Calculate next run
            self._update_next_run(schedule)

            # Send success notification
            if schedule.get('notification_email'):
                await self._send_notification(
                    schedule['notification_email'],
                    f"Backup Success: {schedule_id}",
                    f"Scheduled backup {schedule_id} completed successfully.\n"
                    f"Backup ID: {backup_metadata.backup_id}\n"
                    f"Size: {backup_metadata.size_bytes} bytes\n"
                    f"Next run: {schedule['next_run']}"
                )

            logger.info(f"Scheduled backup {schedule_id} completed successfully")

        except Exception as e:
            logger.error(f"Scheduled backup {schedule_id} failed: {e}")

            # Update failure status
            schedule['last_run'] = datetime.utcnow().isoformat()
            schedule['last_status'] = 'failed'
            schedule['consecutive_failures'] = schedule.get('consecutive_failures', 0) + 1

            # If too many consecutive failures, disable schedule
            if schedule['consecutive_failures'] >= 3:
                schedule['status'] = 'disabled'
                logger.error(f"Schedule {schedule_id} disabled due to {schedule['consecutive_failures']} consecutive failures")

            # Send failure notification
            if schedule.get('notification_email'):
                await self._send_notification(
                    schedule['notification_email'],
                    f"Backup Failed: {schedule_id}",
                    f"Scheduled backup {schedule_id} failed.\n"
                    f"Error: {str(e)}\n"
                    f"Consecutive failures: {schedule['consecutive_failures']}\n"
                    f"Schedule status: {schedule['status']}"
                )

        finally:
            self._save_schedules()

    def _update_next_run(self, schedule: Dict):
        """Update the next run time for a schedule"""
        last_run = datetime.fromisoformat(schedule['last_run'])

        if schedule['schedule_type'] == 'daily':
            next_run = last_run + timedelta(days=1)
        elif schedule['schedule_type'] == 'weekly':
            next_run = last_run + timedelta(days=7)
        elif schedule['schedule_type'] == 'monthly':
            # Add one month
            if last_run.month == 12:
                next_run = last_run.replace(year=last_run.year + 1, month=1)
            else:
                next_run = last_run.replace(month=last_run.month + 1)
        else:
            # Default to daily
            next_run = last_run + timedelta(days=1)

        schedule['next_run'] = next_run.isoformat()

    async def _send_notification(self, to_email: str, subject: str, body: str):
        """Send email notification"""
        if not all([self.smtp_username, self.smtp_password]):
            logger.warning("SMTP credentials not configured, skipping email notification")
            return

        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_username
            msg['To'] = to_email
            msg['Subject'] = f"IIT ML Service - {subject}"

            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            text = msg.as_string()
            server.sendmail(self.smtp_username, to_email, text)
            server.quit()

            logger.info(f"Notification sent to {to_email}")

        except Exception as e:
            logger.error(f"Failed to send notification email: {e}")

    async def run_scheduler(self):
        """Main scheduler loop"""
        logger.info("Starting backup scheduler")

        while True:
            try:
                # Check for due schedules
                due_schedules = self.get_due_schedules()

                # Execute due backups
                for schedule in due_schedules:
                    await self.execute_scheduled_backup(schedule)

                # Clean up old backups
                deleted_count = backup_manager.cleanup_old_backups()
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} old backups")

                # Wait for next check (every 5 minutes)
                await asyncio.sleep(300)

            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

# Global scheduler instance
backup_scheduler = BackupScheduler()

async def main():
    """Main entry point for running the backup scheduler"""
    await backup_scheduler.run_scheduler()

if __name__ == "__main__":
    asyncio.run(main())
