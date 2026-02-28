#!/usr/bin/env python
"""
RQ Worker Script for IHVN ML Service

Run this script to start a background worker for processing queued jobs.

Usage:
    # Run with default settings
    python run_worker.py

    # Run with custom queue name
    python run_worker.py --queue custom_queue

    # Run with custom name
    python run_worker.py --name worker-1

    # Run with scheduler
    python run_worker.py --with-scheduler

    # Run in burst mode (exit when no jobs)
    python run_worker.py --burst
"""
import sys
import os
import argparse
import logging
from rq import Worker
from rq.worker import WorkerStatus

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.queue.worker import get_worker, get_redis_connection

# Optional scheduler imports (may not be available due to compatibility issues)
try:
    from app.queue.scheduler import get_scheduler, start_scheduler
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False
    get_scheduler = None
    start_scheduler = None

from app.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('worker.log')
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point for the worker"""
    parser = argparse.ArgumentParser(
        description='RQ Worker for IHVN ML Service'
    )
    parser.add_argument(
        '--queue',
        type=str,
        default=settings.queue_name,
        help=f'Queue name (default: {settings.queue_name})'
    )
    parser.add_argument(
        '--name',
        type=str,
        default=None,
        help='Worker name (default: auto-generated)'
    )
    parser.add_argument(
        '--with-scheduler',
        action='store_true',
        help='Run with scheduler'
    )
    parser.add_argument(
        '--burst',
        action='store_true',
        help='Run in burst mode (exit when no jobs)'
    )
    parser.add_argument(
        '--log-level',
        type=str,
        default=settings.log_level,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Log level'
    )
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level.upper()))
    
    logger.info("=" * 60)
    logger.info("Starting RQ Worker for IHVN ML Service")
    logger.info("=" * 60)
    logger.info(f"Queue: {args.queue}")
    logger.info(f"Worker Name: {args.name or 'auto-generated'}")
    logger.info(f"Scheduler: {'Enabled' if args.with_scheduler else 'Disabled'}")
    logger.info(f"Burst Mode: {'Enabled' if args.burst else 'Disabled'}")
    logger.info(f"Log Level: {args.log_level}")
    logger.info("=" * 60)
    
    # Check Redis connection
    try:
        redis_conn = get_redis_connection()
        redis_conn.ping()
        logger.info("Redis connection successful")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        logger.error("Please ensure Redis is running and accessible")
        sys.exit(1)
    
    # Start scheduler if requested
    if args.with_scheduler:
        if not SCHEDULER_AVAILABLE:
            logger.error("Scheduler is not available due to dependency compatibility issues")
            logger.error("Please install compatible versions of rq and rq-scheduler")
            logger.error("The basic queue worker will start instead")
        else:
            logger.info("Starting scheduler...")
            try:
                scheduler = get_scheduler()
                
                # Import jobs to register them
                from app.queue import jobs
                
                logger.info("Scheduler started successfully")
                
                # Run scheduler (blocking)
                scheduler.run()
                return
            
            except Exception as e:
                logger.error(f"Failed to start scheduler: {e}")
                sys.exit(1)
    
    # Start worker
    try:
        worker = get_worker(
            queue_names=[args.queue],
            name=args.name
        )
        
        logger.info(f"Worker '{worker.name}' starting...")
        logger.info(f"Listening on queue(s): {', '.join(args.queue)}")
        logger.info("Press Ctrl+C to stop the worker")
        
        # Work loop
        worker.work(
            burst=args.burst,
            logging_level=args.log_level.upper()
        )
    
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Worker failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
    
    logger.info("Worker shutdown complete")


if __name__ == '__main__':
    main()
