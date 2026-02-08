#!/usr/bin/env python3
"""
Database initialization script for IIT ML Service
"""
import sys
import os
import logging

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    """Initialize the database by creating all tables"""
    try:
        from app.core.db import init_database as create_tables
        from app.models import Base
        from sqlalchemy import create_engine

        # Import settings to get database URL
        from app.config import get_settings
        settings = get_settings()

        logger.info("Initializing database...")
        logger.info(f"Database URL: {settings.database_url}")

        # Create engine and create tables
        engine = create_engine(settings.database_url, echo=True)

        # Create all tables
        Base.metadata.create_all(bind=engine)

        logger.info("Database tables created successfully!")

        # Verify tables were created
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f"Created tables: {tables}")

        return True

    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
