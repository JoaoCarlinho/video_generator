"""
Database Reset Script

This script drops all existing tables and recreates them with the updated schema
that enforces the Brand → Product → Campaign → Creative hierarchy.

Usage:
    python reset_database.py

WARNING: This will DELETE ALL DATA in the database!
"""

import sys
import os
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.pool import NullPool
import logging

from app.config import settings
from app.database.models import Base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def drop_all_tables(engine):
    """Drop all existing tables in the database."""
    logger.info("🗑️  Dropping all existing tables...")

    try:
        # Get inspector to check existing tables
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        if not existing_tables:
            logger.info("ℹ️  No existing tables found")
            return True

        logger.info(f"📋 Found {len(existing_tables)} existing tables: {', '.join(existing_tables)}")

        with engine.begin() as conn:
            # Drop all tables using CASCADE to handle foreign keys
            for table in existing_tables:
                logger.info(f"  Dropping table: {table}")
                conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))

            # Also drop alembic version table if it exists
            conn.execute(text('DROP TABLE IF EXISTS alembic_version CASCADE'))

        logger.info("✅ All tables dropped successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to drop tables: {e}", exc_info=True)
        return False


def create_all_tables(engine):
    """Create all tables from the current models."""
    logger.info("🏗️  Creating new tables with updated schema...")

    try:
        # First, create the auth schema if it doesn't exist
        # This is needed for the AuthUser model which references auth.users
        with engine.begin() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS auth"))
            logger.info("  ✓ Created/verified auth schema")

        # Create all tables defined in Base.metadata
        Base.metadata.create_all(bind=engine)

        # Verify tables were created
        inspector = inspect(engine)
        created_tables = inspector.get_table_names()

        logger.info(f"✅ Created {len(created_tables)} tables:")
        for table in created_tables:
            logger.info(f"  ✓ {table}")

        # Also check auth schema tables
        auth_tables = inspector.get_table_names(schema='auth')
        if auth_tables:
            logger.info(f"✅ Created {len(auth_tables)} tables in auth schema:")
            for table in auth_tables:
                logger.info(f"  ✓ auth.{table}")

        return True

    except Exception as e:
        logger.error(f"❌ Failed to create tables: {e}", exc_info=True)
        return False


def verify_schema(engine):
    """Verify the new schema is correct."""
    logger.info("🔍 Verifying database schema...")

    try:
        inspector = inspect(engine)

        # Check expected tables exist
        expected_tables = {'brands', 'products', 'campaigns', 'creatives'}
        existing_tables = set(inspector.get_table_names())

        missing_tables = expected_tables - existing_tables
        if missing_tables:
            logger.error(f"❌ Missing tables: {', '.join(missing_tables)}")
            return False

        # Check foreign keys
        logger.info("📊 Checking foreign key relationships:")

        # Products should have brand_id FK
        products_fks = inspector.get_foreign_keys('products')
        brand_fk = next((fk for fk in products_fks if 'brand_id' in fk['constrained_columns']), None)
        if brand_fk:
            logger.info(f"  ✓ products.brand_id → {brand_fk['referred_table']}.{brand_fk['referred_columns'][0]}")
        else:
            logger.error("  ✗ Missing foreign key: products.brand_id → brands.id")
            return False

        # Campaigns should have product_id FK
        campaigns_fks = inspector.get_foreign_keys('campaigns')
        product_fk = next((fk for fk in campaigns_fks if 'product_id' in fk['constrained_columns']), None)
        if product_fk:
            logger.info(f"  ✓ campaigns.product_id → {product_fk['referred_table']}.{product_fk['referred_columns'][0]}")
        else:
            logger.error("  ✗ Missing foreign key: campaigns.product_id → products.id")
            return False

        # Creatives should have campaign_id FK
        creatives_fks = inspector.get_foreign_keys('creatives')
        campaign_fk = next((fk for fk in creatives_fks if 'campaign_id' in fk['constrained_columns']), None)
        if campaign_fk:
            logger.info(f"  ✓ creatives.campaign_id → {campaign_fk['referred_table']}.{campaign_fk['referred_columns'][0]}")
        else:
            logger.error("  ✗ Missing foreign key: creatives.campaign_id → campaigns.id")
            return False

        logger.info("✅ Schema verification passed!")
        return True

    except Exception as e:
        logger.error(f"❌ Schema verification failed: {e}", exc_info=True)
        return False


def reset_database():
    """Main function to reset the database."""
    logger.info("=" * 80)
    logger.info("DATABASE RESET - Brand → Product → Campaign → Creative Hierarchy")
    logger.info("=" * 80)

    # Check if DATABASE_URL is set
    if not settings.database_url:
        logger.error("❌ DATABASE_URL environment variable is not set!")
        logger.error("Please set it in your .env file")
        return False

    # Show database URL (masked password)
    masked_url = settings.database_url
    if '@' in masked_url:
        parts = masked_url.split('@')
        if ':' in parts[0]:
            user_pass = parts[0].split(':')
            masked_url = f"{user_pass[0]}:****@{parts[1]}"

    logger.info(f"📍 Database: {masked_url}")

    # Confirm action
    logger.warning("")
    logger.warning("⚠️  WARNING: This will DELETE ALL DATA in the database!")
    logger.warning("")
    response = input("Type 'yes' to continue: ")

    if response.lower() != 'yes':
        logger.info("❌ Operation cancelled")
        return False

    logger.info("")

    try:
        # Create engine
        logger.info("🔌 Connecting to database...")

        # Determine if we need SSL
        db_url = settings.database_url
        is_local = any(x in db_url for x in ['localhost', '127.0.0.1', '@10.0.'])

        connect_args = {
            'connect_timeout': 10,
            'options': '-c client_encoding=UTF8'
        }

        if is_local:
            if '?' in db_url:
                db_url += '&sslmode=disable'
            else:
                db_url += '?sslmode=disable'
            connect_args['sslmode'] = 'disable'
        else:
            if '?' in db_url:
                db_url += '&sslmode=require'
            else:
                db_url += '?sslmode=require'

        engine = create_engine(
            db_url,
            poolclass=NullPool,
            echo=False,
            connect_args=connect_args
        )

        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Connected to database")
        logger.info("")

        # Step 1: Drop all tables
        if not drop_all_tables(engine):
            logger.error("❌ Failed to drop tables")
            return False
        logger.info("")

        # Step 2: Create all tables
        if not create_all_tables(engine):
            logger.error("❌ Failed to create tables")
            return False
        logger.info("")

        # Step 3: Verify schema
        if not verify_schema(engine):
            logger.error("❌ Schema verification failed")
            return False
        logger.info("")

        logger.info("=" * 80)
        logger.info("✅ DATABASE RESET COMPLETED SUCCESSFULLY!")
        logger.info("=" * 80)
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. The database now has the correct hierarchy schema")
        logger.info("2. Brand → Product → Campaign → Creative relationships enforced")
        logger.info("3. All foreign keys have CASCADE delete configured")
        logger.info("")

        return True

    except Exception as e:
        logger.error(f"❌ Database reset failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = reset_database()
    sys.exit(0 if success else 1)
