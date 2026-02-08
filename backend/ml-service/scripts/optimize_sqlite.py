#!/usr/bin/env python3
"""
Simple SQLite database optimization for IIT ML Service
Optimizes SQLite database for development
"""
import sqlite3
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

def optimize_sqlite_database(db_path: str = "./iit_ml_service.db"):
    """
    Optimize SQLite database for better performance
    
    Args:
        db_path: Path to SQLite database file
    """
    logger.info(f"Optimizing SQLite database: {db_path}")
    
    if not os.path.exists(db_path):
        logger.warning(f"Database file not found: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Enable WAL mode for better concurrency
        cursor.execute("PRAGMA journal_mode = WAL;")
        logger.info("WAL mode enabled")
        
        # Enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys = ON;")
        logger.info("Foreign key constraints enabled")
        
        # Optimize cache size (10MB)
        cursor.execute("PRAGMA cache_size = -10000;")
        logger.info("Cache size optimized to 10MB")
        
        # Set synchronous mode to NORMAL for better performance
        cursor.execute("PRAGMA synchronous = NORMAL;")
        logger.info("Synchronous mode set to NORMAL")
        
        # Set temp store to MEMORY
        cursor.execute("PRAGMA temp_store = MEMORY;")
        logger.info("Temp store set to MEMORY")
        
        # Get table list
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [row[0] for row in cursor.fetchall()]
        logger.info(f"Found {len(tables)} tables to optimize")
        
        # Create indexes on commonly queried columns
        indexes_created = []
        
        # Patient table indexes
        if 'patients' in tables:
            try:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_patients_state ON patients(state_province);")
                indexes_created.append("idx_patients_state")
            except Exception as e:
                logger.warning(f"Could not create idx_patients_state: {e}")
        
        # Observations table indexes
        if 'observations' in tables:
            try:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_observations_patient ON observations(patient_uuid);")
                indexes_created.append("idx_observations_patient")
            except Exception as e:
                logger.warning(f"Could not create idx_observations_patient: {e}")
            
            try:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_observations_datetime ON observations(obs_datetime DESC);")
                indexes_created.append("idx_observations_datetime")
            except Exception as e:
                logger.warning(f"Could not create idx_observations_datetime: {e}")
        
        # Predictions table indexes
        if 'iit_predictions' in tables:
            try:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_predictions_timestamp ON iit_predictions(prediction_timestamp DESC);")
                indexes_created.append("idx_predictions_timestamp")
            except Exception as e:
                logger.warning(f"Could not create idx_predictions_timestamp: {e}")
        
        # Visits table indexes
        if 'visits' in tables:
            try:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_visits_patient ON visits(patient_uuid);")
                indexes_created.append("idx_visits_patient")
            except Exception as e:
                logger.warning(f"Could not create idx_visits_patient: {e}")
        
        logger.info(f"Created {len(indexes_created)} indexes: {indexes_created}")
        
        # Run ANALYZE to update statistics
        cursor.execute("ANALYZE;")
        logger.info("Database statistics updated (ANALYZE)")
        
        # Run VACUUM to reclaim space
        cursor.execute("VACUUM;")
        logger.info("Database vacuumed (VACUUM)")
        
        conn.commit()
        conn.close()
        
        # Get file size before and after
        db_size = os.path.getsize(db_path)
        db_size_mb = db_size / (1024 * 1024)
        
        logger.info(f"Database optimization completed. Size: {db_size_mb:.2f} MB")
        return True
        
    except Exception as e:
        logger.error(f"Database optimization failed: {str(e)}")
        return False

def check_database_health(db_path: str = "./iit_ml_service.db") -> dict:
    """
    Check database health and return statistics
    
    Args:
        db_path: Path to SQLite database file
    
    Returns:
        dict: Database health information
    """
    logger.info(f"Checking database health: {db_path}")
    
    health_info = {
        "database_path": db_path,
        "exists": False,
        "size_bytes": 0,
        "size_mb": 0,
        "table_count": 0,
        "tables": [],
        "index_count": 0,
        "wal_enabled": False,
        "status": "unknown"
    }
    
    if not os.path.exists(db_path):
        health_info["status"] = "not_found"
        return health_info
    
    try:
        health_info["exists"] = True
        health_info["size_bytes"] = os.path.getsize(db_path)
        health_info["size_mb"] = health_info["size_bytes"] / (1024 * 1024)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check WAL mode
        cursor.execute("PRAGMA journal_mode;")
        wal_mode = cursor.fetchone()[0]
        health_info["wal_enabled"] = (wal_mode == "wal")
        
        # Get table list
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [row[0] for row in cursor.fetchall()]
        health_info["table_count"] = len(tables)
        health_info["tables"] = tables
        
        # Get index count
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%';")
        health_info["index_count"] = cursor.fetchone()[0]
        
        conn.close()
        
        health_info["status"] = "healthy"
        logger.info(f"Database health check completed. Status: {health_info['status']}")
        
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        health_info["status"] = "error"
        health_info["error"] = str(e)
    
    return health_info

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Check database health first
    health = check_database_health()
    print("\n=== Database Health ===")
    print(f"Status: {health['status']}")
    print(f"Size: {health['size_mb']:.2f} MB")
    print(f"Tables: {health['table_count']}")
    print(f"Indexes: {health['index_count']}")
    print(f"WAL Mode: {health['wal_enabled']}")
    
    # Optimize database
    print("\n=== Optimizing Database ===")
    success = optimize_sqlite_database()
    
    if success:
        print("\n=== Optimization Complete ===")
        # Check health again
        health_after = check_database_health()
        print(f"Size after: {health_after['size_mb']:.2f} MB")
    else:
        print("\n=== Optimization Failed ===")
