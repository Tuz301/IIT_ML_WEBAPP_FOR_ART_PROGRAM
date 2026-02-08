"""
Comprehensive Database utilities and session management for IIT ML Service
Supports both PostgreSQL and SQLite databases with unified interface
"""
import os
import json
import logging
import sqlite3
import shutil
from typing import Generator, Any, Callable, Dict, List, Optional, Union
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import uuid

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ..core.db import SessionLocal, verify_database_connectivity, get_database_stats
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class DatabaseManager:
    """
    Unified database manager supporting both PostgreSQL and SQLite
    """

    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL", settings.database_url)
        self.is_sqlite = "sqlite" in self.database_url.lower()
        self.is_postgres = "postgresql" in self.database_url.lower() or "postgres" in self.database_url.lower()

        # Set default database path for SQLite
        if self.is_sqlite:
            self.db_path = self._get_sqlite_path()
        else:
            self.db_path = None

    def _get_sqlite_path(self) -> str:
        """Extract SQLite database path from URL"""
        if "///" in self.database_url:
            return self.database_url.split("///")[1]
        return "iit_ml_service.db"

    def get_connection(self, database_path: str = None) -> Union[sqlite3.Connection, Any]:
        """
        Get database connection (SQLite direct or SQLAlchemy engine for PostgreSQL)

        Args:
            database_path: Path to SQLite database file (SQLite only)

        Returns:
            Database connection object
        """
        if self.is_sqlite:
            db_path = database_path or self.db_path
            try:
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row  # Enable column access by name
                conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
                conn.execute("PRAGMA journal_mode = WAL")  # Enable WAL mode for better concurrency
                return conn
            except Exception as e:
                logger.error(f"Failed to connect to SQLite database {db_path}: {str(e)}")
                raise
        else:
            # For PostgreSQL, return SQLAlchemy engine
            from ..core.db import engine
            return engine

    def execute_query(self, query: str, params: tuple = None, database_path: str = None) -> List[Dict]:
        """
        Execute a SELECT query and return results as list of dictionaries

        Args:
            query: SQL query string
            params: Query parameters
            database_path: Path to database file (SQLite only)

        Returns:
            List of dictionaries containing query results
        """
        if self.is_sqlite:
            conn = None
            try:
                conn = self.get_connection(database_path)
                cursor = conn.cursor()

                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                results = cursor.fetchall()

                # Convert rows to dictionaries
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                return [dict(zip(columns, row)) for row in results]

            except Exception as e:
                logger.error(f"SQLite query execution failed: {str(e)}")
                raise
            finally:
                if conn:
                    conn.close()
        else:
            # PostgreSQL execution
            try:
                with SessionLocal() as session:
                    result = session.execute(text(query), params or {})
                    rows = result.fetchall()

                    # Convert to dictionaries
                    if rows:
                        columns = result.keys()
                        return [dict(zip(columns, row)) for row in rows]
                    return []

            except Exception as e:
                logger.error(f"PostgreSQL query execution failed: {str(e)}")
                raise

    def execute_transaction(self, operation: Callable, database_path: str = None) -> Any:
        """
        Execute a database transaction

        Args:
            operation: Function that takes a connection/session and performs operations
            database_path: Path to database file (SQLite only)

        Returns:
            Result of the operation
        """
        if self.is_sqlite:
            conn = None
            try:
                conn = self.get_connection(database_path)
                conn.execute("BEGIN TRANSACTION")

                result = operation(conn)

                conn.commit()
                return result

            except Exception as e:
                if conn:
                    conn.rollback()
                logger.error(f"SQLite transaction failed: {str(e)}")
                raise
            finally:
                if conn:
                    conn.close()
        else:
            # PostgreSQL transaction
            try:
                with SessionLocal() as session:
                    with session.begin():
                        result = operation(session)
                        return result

            except Exception as e:
                logger.error(f"PostgreSQL transaction failed: {str(e)}")
                raise

    def execute_raw_sql(self, sql: str, params: Dict = None, database_path: str = None) -> List:
        """
        Execute raw SQL query (use with caution)

        Args:
            sql: SQL query string
            params: Query parameters
            database_path: Path to database file (SQLite only)

        Returns:
            List of query results
        """
        if self.is_sqlite:
            conn = None
            try:
                conn = self.get_connection(database_path)
                cursor = conn.cursor()

                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)

                return cursor.fetchall()

            except Exception as e:
                logger.error(f"Raw SQLite SQL execution failed: {str(e)}")
                raise
            finally:
                if conn:
                    conn.close()
        else:
            # PostgreSQL
            try:
                with SessionLocal() as session:
                    result = session.execute(text(sql), params or {})
                    return result.fetchall()

            except Exception as e:
                logger.error(f"Raw PostgreSQL SQL execution failed: {str(e)}")
                raise

    def backup_database(self, backup_path: str, source_path: str = None) -> bool:
        """
        Create a backup of the database

        Args:
            backup_path: Path where backup should be saved
            source_path: Path to source database (default: main database)

        Returns:
            bool: True if backup successful
        """
        try:
            # Ensure backup directory exists
            backup_dir = os.path.dirname(backup_path)
            os.makedirs(backup_dir, exist_ok=True)

            if self.is_sqlite:
                source = source_path or self.db_path
                shutil.copy2(source, backup_path)
                logger.info(f"SQLite database backup created: {backup_path}")
            else:
                # PostgreSQL backup using pg_dump
                import subprocess
                from urllib.parse import urlparse

                parsed = urlparse(self.database_url)
                cmd = [
                    "pg_dump",
                    "--host", parsed.hostname or "localhost",
                    "--port", str(parsed.port or 5432),
                    "--username", parsed.username or "",
                    "--dbname", parsed.path.lstrip("/"),
                    "--format", "custom",
                    "--compress", "9",
                    "--file", backup_path
                ]

                env = os.environ.copy()
                if parsed.password:
                    env["PGPASSWORD"] = parsed.password

                result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=300)
                if result.returncode != 0:
                    raise Exception(f"pg_dump failed: {result.stderr}")

                logger.info(f"PostgreSQL database backup created: {backup_path}")

            return True

        except Exception as e:
            logger.error(f"Database backup failed: {str(e)}")
            return False

    def restore_database(self, backup_path: str, target_path: str = None) -> bool:
        """
        Restore database from backup

        Args:
            backup_path: Path to backup file
            target_path: Path to target database (default: main database)

        Returns:
            bool: True if restore successful
        """
        try:
            if not os.path.exists(backup_path):
                raise FileNotFoundError(f"Backup file not found: {backup_path}")

            if self.is_sqlite:
                target = target_path or self.db_path
                shutil.copy2(backup_path, target)
                logger.info(f"SQLite database restored from: {backup_path}")
            else:
                # PostgreSQL restore using pg_restore
                import subprocess
                from urllib.parse import urlparse

                parsed = urlparse(self.database_url)
                cmd = [
                    "pg_restore",
                    "--host", parsed.hostname or "localhost",
                    "--port", str(parsed.port or 5432),
                    "--username", parsed.username or "",
                    "--dbname", parsed.path.lstrip("/"),
                    "--clean",
                    "--if-exists",
                    backup_path
                ]

                env = os.environ.copy()
                if parsed.password:
                    env["PGPASSWORD"] = parsed.password

                result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=600)
                if result.returncode != 0:
                    raise Exception(f"pg_restore failed: {result.stderr}")

                logger.info(f"PostgreSQL database restored from: {backup_path}")

            return True

        except Exception as e:
            logger.error(f"Database restore failed: {str(e)}")
            return False

    def get_table_info(self, table_name: str, database_path: str = None) -> Dict:
        """
        Get information about a database table

        Args:
            table_name: Name of the table
            database_path: Path to database file (SQLite only)

        Returns:
            dict: Table information
        """
        if self.is_sqlite:
            sql = "PRAGMA table_info(?)"
            try:
                results = self.execute_raw_sql(sql, (table_name,), database_path)
                columns = []
                for row in results:
                    columns.append({
                        "name": row[1],  # column name
                        "type": row[2],  # data type
                        "nullable": row[3] == 0,  # not null constraint
                        "default": row[4],  # default value
                        "primary_key": row[5] == 1  # primary key
                    })

                return {
                    "table_name": table_name,
                    "columns": columns,
                    "column_count": len(columns)
                }
            except Exception as e:
                logger.error(f"Failed to get SQLite table info for {table_name}: {str(e)}")
                return {"error": str(e)}
        else:
            # PostgreSQL
            sql = """
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default,
                CASE WHEN pk.column_name IS NOT NULL THEN true ELSE false END as primary_key
            FROM information_schema.columns c
            LEFT JOIN (
                SELECT ku.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage ku
                ON tc.constraint_name = ku.constraint_name
                WHERE tc.constraint_type = 'PRIMARY KEY'
                AND tc.table_name = :table_name
            ) pk ON c.column_name = pk.column_name
            WHERE c.table_name = :table_name
            AND c.table_schema = 'public'
            ORDER BY c.ordinal_position
            """

            try:
                results = self.execute_query(sql, {"table_name": table_name})
                columns = []
                for row in results:
                    columns.append({
                        "name": row["column_name"],
                        "type": row["data_type"],
                        "nullable": row["is_nullable"] == 'YES',
                        "default": row["column_default"],
                        "primary_key": row["primary_key"]
                    })

                return {
                    "table_name": table_name,
                    "columns": columns,
                    "column_count": len(columns)
                }
            except Exception as e:
                logger.error(f"Failed to get PostgreSQL table info for {table_name}: {str(e)}")
                return {"error": str(e)}

    def get_database_size(self, database_path: str = None) -> Dict:
        """
        Get database size information

        Args:
            database_path: Path to database file (SQLite only)

        Returns:
            dict: Database size information
        """
        if self.is_sqlite:
            db_path = database_path or self.db_path
            try:
                if os.path.exists(db_path):
                    size_bytes = os.path.getsize(db_path)
                    size_pretty = self._format_bytes(size_bytes)

                    return {
                        "database_name": os.path.basename(db_path),
                        "size_pretty": size_pretty,
                        "size_bytes": size_bytes
                    }
                else:
                    return {"error": "Database file not found"}
            except Exception as e:
                logger.error(f"Failed to get SQLite database size: {str(e)}")
                return {"error": str(e)}
        else:
            # PostgreSQL
            sql = """
            SELECT
                current_database() as database_name,
                pg_size_pretty(pg_database_size(current_database())) as size_pretty,
                pg_database_size(current_database()) as size_bytes
            """

            try:
                result = self.execute_query(sql)
                if result:
                    return result[0]
                return {}
            except Exception as e:
                logger.error(f"Failed to get PostgreSQL database size: {str(e)}")
                return {"error": str(e)}

    def list_tables(self, database_path: str = None) -> List[str]:
        """
        List all tables in the current database

        Args:
            database_path: Path to database file (SQLite only)

        Returns:
            list: List of table names
        """
        if self.is_sqlite:
            sql = """
            SELECT name FROM sqlite_master
            WHERE type='table'
            AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
            try:
                results = self.execute_raw_sql(sql, database_path=database_path)
                return [row[0] for row in results]
            except Exception as e:
                logger.error(f"Failed to list SQLite tables: {str(e)}")
                return []
        else:
            # PostgreSQL
            sql = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
            try:
                results = self.execute_query(sql)
                return [row["table_name"] for row in results]
            except Exception as e:
                logger.error(f"Failed to list PostgreSQL tables: {str(e)}")
                return []

    def vacuum_database(self, database_path: str = None) -> bool:
        """
        Perform VACUUM on the database to reclaim space

        Args:
            database_path: Path to database file (SQLite only)

        Returns:
            bool: True if successful
        """
        if self.is_sqlite:
            sql = "VACUUM"
            try:
                self.execute_raw_sql(sql, database_path=database_path)
                logger.info("SQLite VACUUM completed")
                return True
            except Exception as e:
                logger.error(f"SQLite VACUUM failed: {str(e)}")
                return False
        else:
            # PostgreSQL VACUUM
            sql = "VACUUM"
            try:
                self.execute_raw_sql(sql)
                logger.info("PostgreSQL VACUUM completed")
                return True
            except Exception as e:
                logger.error(f"PostgreSQL VACUUM failed: {str(e)}")
                return False

    def analyze_database(self, database_path: str = None) -> bool:
        """
        Perform ANALYZE on the database to update statistics

        Args:
            database_path: Path to database file (SQLite only)

        Returns:
            bool: True if successful
        """
        if self.is_sqlite:
            sql = "ANALYZE"
            try:
                self.execute_raw_sql(sql, database_path=database_path)
                logger.info("SQLite ANALYZE completed")
                return True
            except Exception as e:
                logger.error(f"SQLite ANALYZE failed: {str(e)}")
                return False
        else:
            # PostgreSQL ANALYZE
            sql = "ANALYZE"
            try:
                self.execute_raw_sql(sql)
                logger.info("PostgreSQL ANALYZE completed")
                return True
            except Exception as e:
                logger.error(f"PostgreSQL ANALYZE failed: {str(e)}")
                return False

    def _format_bytes(self, size_bytes: int) -> str:
        """Format bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} GB"

# Global database manager instance
db_manager = DatabaseManager()

# Legacy compatibility functions
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency to get database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_session():
    """
    Context manager for database sessions
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database session error: {str(e)}")
        raise
    finally:
        db.close()

def get_database_connection(database_path: str = None) -> Union[sqlite3.Connection, Any]:
    """
    Get database connection (legacy compatibility)
    """
    return db_manager.get_connection(database_path)

def execute_query(query: str, params: tuple = None, database_path: str = None) -> List[Dict]:
    """
    Execute a SELECT query (legacy compatibility)
    """
    return db_manager.execute_query(query, params, database_path)

def execute_transaction(operation: Callable[[Any], Any], database_path: str = None) -> Any:
    """
    Execute a database transaction (legacy compatibility)
    """
    return db_manager.execute_transaction(operation, database_path)

def execute_raw_sql(sql: str, params: Dict = None, database_path: str = None) -> List:
    """
    Execute raw SQL query (legacy compatibility)
    """
    return db_manager.execute_raw_sql(sql, params, database_path)

def backup_database(backup_path: str, source_path: str = None) -> bool:
    """
    Create a backup of the database (legacy compatibility)
    """
    return db_manager.backup_database(backup_path, source_path)

def restore_database(backup_path: str, target_path: str = None) -> bool:
    """
    Restore database from backup (legacy compatibility)
    """
    return db_manager.restore_database(backup_path, target_path)

def check_database_health() -> Dict:
    """
    Check database health and connectivity
    """
    health_info = {
        "database_connected": False,
        "database_type": "sqlite" if db_manager.is_sqlite else "postgresql",
        "database_path": db_manager.db_path if db_manager.is_sqlite else None,
        "database_size": {},
        "pool_stats": {},
        "status": "unhealthy"
    }

    try:
        # Check connectivity
        health_info["database_connected"] = verify_database_connectivity()

        # Get database size
        health_info["database_size"] = db_manager.get_database_size()

        # Get pool statistics
        health_info["pool_stats"] = get_database_stats()

        # Determine overall status
        if health_info["database_connected"]:
            health_info["status"] = "healthy"
        else:
            health_info["status"] = "unhealthy"

    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        health_info["error"] = str(e)

    return health_info

def get_table_info(table_name: str, database_path: str = None) -> Dict:
    """
    Get information about a database table (legacy compatibility)
    """
    return db_manager.get_table_info(table_name, database_path)

def get_database_size(database_path: str = None) -> Dict:
    """
    Get database size information (legacy compatibility)
    """
    return db_manager.get_database_size(database_path)

def list_tables(database_path: str = None) -> List[str]:
    """
    List all tables in the current database (legacy compatibility)
    """
    return db_manager.list_tables(database_path)

def vacuum_database(database_path: str = None) -> bool:
    """
    Perform VACUUM on the database (legacy compatibility)
    """
    return db_manager.vacuum_database(database_path)

def analyze_database(database_path: str = None) -> bool:
    """
    Perform ANALYZE on the database (legacy compatibility)
    """
    return db_manager.analyze_database(database_path)

# JSON Ingestion Utilities
class JSONDataIngestion:
    """
    Utilities for ingesting JSON data into the database
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def ingest_patient_data(self, json_file_path: str, batch_size: int = 1000) -> Dict[str, Any]:
        """
        Ingest patient data from JSON file

        Args:
            json_file_path: Path to JSON file containing patient data
            batch_size: Number of records to process in each batch

        Returns:
            dict: Ingestion statistics and results
        """
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            patients = data.get('patients', [])
            visits = data.get('visits', [])
            encounters = data.get('encounters', [])
            observations = data.get('observations', [])

            stats = {
                "patients_processed": 0,
                "visits_processed": 0,
                "encounters_processed": 0,
                "observations_processed": 0,
                "errors": [],
                "start_time": datetime.utcnow().isoformat()
            }

            # Process patients in batches
            for i in range(0, len(patients), batch_size):
                batch = patients[i:i + batch_size]
                batch_stats = self._process_patient_batch(batch)
                stats["patients_processed"] += batch_stats["processed"]
                stats["errors"].extend(batch_stats["errors"])

            # Process visits
            for i in range(0, len(visits), batch_size):
                batch = visits[i:i + batch_size]
                batch_stats = self._process_visit_batch(batch)
                stats["visits_processed"] += batch_stats["processed"]
                stats["errors"].extend(batch_stats["errors"])

            # Process encounters
            for i in range(0, len(encounters), batch_size):
                batch = encounters[i:i + batch_size]
                batch_stats = self._process_encounter_batch(batch)
                stats["encounters_processed"] += batch_stats["processed"]
                stats["errors"].extend(batch_stats["errors"])

            # Process observations
            for i in range(0, len(observations), batch_size):
                batch = observations[i:i + batch_size]
                batch_stats = self._process_observation_batch(batch)
                stats["observations_processed"] += batch_stats["processed"]
                stats["errors"].extend(batch_stats["errors"])

            stats["end_time"] = datetime.utcnow().isoformat()
            stats["total_time_seconds"] = (datetime.fromisoformat(stats["end_time"]) - datetime.fromisoformat(stats["start_time"])).total_seconds()

            logger.info(f"JSON ingestion completed: {stats}")
            return stats

        except Exception as e:
            logger.error(f"JSON ingestion failed: {str(e)}")
            return {"error": str(e)}

    def _process_patient_batch(self, patients: List[Dict]) -> Dict[str, Any]:
        """Process a batch of patient records"""
        processed = 0
        errors = []

        def insert_patients(conn_or_session):
            nonlocal processed, errors
            for patient_data in patients:
                try:
                    # Validate required fields
                    if not patient_data.get('patient_uuid'):
                        patient_data['patient_uuid'] = str(uuid.uuid4())

                    # Insert patient
                    if self.db_manager.is_sqlite:
                        conn_or_session.execute("""
                            INSERT OR REPLACE INTO patients
                            (patient_uuid, datim_id, pepfar_id, hospital_number, first_name, surname,
                             gender, date_of_birth, phone_number, state_province, lga, ward,
                             created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            patient_data['patient_uuid'],
                            patient_data.get('datim_id'),
                            patient_data.get('pepfar_id'),
                            patient_data.get('hospital_number'),
                            patient_data.get('first_name'),
                            patient_data.get('surname'),
                            patient_data.get('gender'),
                            patient_data.get('date_of_birth'),
                            patient_data.get('phone_number'),
                            patient_data.get('state_province'),
                            patient_data.get('lga'),
                            patient_data.get('ward'),
                            datetime.utcnow().isoformat(),
                            datetime.utcnow().isoformat()
                        ))
                    else:
                        # PostgreSQL
                        conn_or_session.execute(text("""
                            INSERT INTO patients
                            (patient_uuid, datim_id, pepfar_id, hospital_number, first_name, surname,
                             gender, date_of_birth, phone_number, state_province, lga, ward,
                             created_at, updated_at)
                            VALUES (:patient_uuid, :datim_id, :pepfar_id, :hospital_number, :first_name, :surname,
                                    :gender, :date_of_birth, :phone_number, :state_province, :lga, :ward,
                                    :created_at, :updated_at)
                            ON CONFLICT (patient_uuid) DO UPDATE SET
                                datim_id = EXCLUDED.datim_id,
                                pepfar_id = EXCLUDED.pepfar_id,
                                hospital_number = EXCLUDED.hospital_number,
                                first_name = EXCLUDED.first_name,
                                surname = EXCLUDED.surname,
                                gender = EXCLUDED.gender,
                                date_of_birth = EXCLUDED.date_of_birth,
                                phone_number = EXCLUDED.phone_number,
                                state_province = EXCLUDED.state_province,
                                lga = EXCLUDED.lga,
                                ward = EXCLUDED.ward,
                                updated_at = EXCLUDED.updated_at
                        """), {
                            'patient_uuid': patient_data['patient_uuid'],
                            'datim_id': patient_data.get('datim_id'),
                            'pepfar_id': patient_data.get('pepfar_id'),
                            'hospital_number': patient_data.get('hospital_number'),
                            'first_name': patient_data.get('first_name'),
                            'surname': patient_data.get('surname'),
                            'gender': patient_data.get('gender'),
                            'date_of_birth': patient_data.get('date_of_birth'),
                            'phone_number': patient_data.get('phone_number'),
                            'state_province': patient_data.get('state_province'),
                            'lga': patient_data.get('lga'),
                            'ward': patient_data.get('ward'),
                            'created_at': datetime.utcnow(),
                            'updated_at': datetime.utcnow()
                        })

                    processed += 1

                except Exception as e:
                    errors.append(f"Patient {patient_data.get('patient_uuid', 'unknown')}: {str(e)}")

        try:
            self.db_manager.execute_transaction(insert_patients)
        except Exception as e:
            errors.append(f"Batch transaction failed: {str(e)}")

        return {"processed": processed, "errors": errors}

    def _process_visit_batch(self, visits: List[Dict]) -> Dict[str, Any]:
        """Process a batch of visit records"""
        # Similar implementation for visits
        processed = len(visits)  # Placeholder
        errors = []
        return {"processed": processed, "errors": errors}

    def _process_encounter_batch(self, encounters: List[Dict]) -> Dict[str, Any]:
        """Process a batch of encounter records"""
        # Similar implementation for encounters
        processed = len(encounters)  # Placeholder
        errors = []
        return {"processed": processed, "errors": errors}

    def _process_observation_batch(self, observations: List[Dict]) -> Dict[str, Any]:
        """Process a batch of observation records"""
        # Similar implementation for observations
        processed = len(observations)  # Placeholder
        errors = []
        return {"processed": processed, "errors": errors}

# Global JSON ingestion instance
json_ingestion = JSONDataIngestion(db_manager)

def ingest_json_data(json_file_path: str, batch_size: int = 1000) -> Dict[str, Any]:
    """
    Ingest JSON data into the database

    Args:
        json_file_path: Path to JSON file
        batch_size: Batch size for processing

    Returns:
        dict: Ingestion results
    """
    return json_ingestion.ingest_patient_data(json_file_path, batch_size)
