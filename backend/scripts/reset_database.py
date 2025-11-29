"""
Reset database script - drops all tables and recreates them from models
"""
import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import app.database.connection as db_conn
from app.database.models import Base
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset_database():
    """Drop all tables and recreate them from models."""
    try:
        # Initialize database connection
        logger.info("🔌 Initializing database connection...")
        db_conn.init_db()

        if db_conn.engine is None:
            logger.error("❌ Failed to initialize database engine")
            return

        # Filter out tables in 'auth' schema (managed by Supabase)
        tables_to_drop = [table for table in Base.metadata.sorted_tables
                        if table.schema != 'auth']

        logger.info(f"🗑️  Dropping {len(tables_to_drop)} tables (excluding auth schema)...")
        for table in reversed(tables_to_drop):  # Drop in reverse order for FK constraints
            logger.info(f"   Dropping {table.name}...")
            table.drop(bind=db_conn.engine, checkfirst=True)
        logger.info("✅ Tables dropped successfully")

        logger.info("🔨 Creating tables from models...")
        tables_to_create = [table for table in Base.metadata.sorted_tables
                          if table.schema != 'auth']
        Base.metadata.create_all(bind=db_conn.engine, tables=tables_to_create)
        logger.info(f"✅ {len(tables_to_create)} tables created successfully")

        logger.info("🎉 Database reset complete!")

    except Exception as e:
        logger.error(f"❌ Database reset failed: {e}")
        raise

if __name__ == "__main__":
    reset_database()
