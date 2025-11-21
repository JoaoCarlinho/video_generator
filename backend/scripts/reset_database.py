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

        logger.info("🗑️  Dropping all tables...")
        Base.metadata.drop_all(bind=db_conn.engine)
        logger.info("✅ All tables dropped successfully")

        logger.info("🔨 Creating all tables from models...")
        Base.metadata.create_all(bind=db_conn.engine)
        logger.info("✅ All tables created successfully")

        logger.info("🎉 Database reset complete!")

    except Exception as e:
        logger.error(f"❌ Database reset failed: {e}")
        raise

if __name__ == "__main__":
    reset_database()
