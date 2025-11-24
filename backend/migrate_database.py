"""
Auto-migration script that runs on startup to add missing columns.
This is safer than dropping all tables - it preserves existing data.
"""

import logging
from sqlalchemy import text, inspect

logger = logging.getLogger(__name__)

def migrate_database():
    """Add missing columns to Campaign table if they don't exist."""
    from app.database.connection import engine
    
    if engine is None:
        logger.warning("⚠️ Database engine not available, skipping migration")
        return False
    
    try:
        with engine.connect() as conn:
            # Check if columns already exist
            inspector = inspect(engine)
            campaign_columns = [col['name'] for col in inspector.get_columns('campaigns')]
            
            migrations_applied = False
            
            # Add progress column if missing
            if 'progress' not in campaign_columns:
                logger.info("📝 Adding 'progress' column to campaigns table...")
                conn.execute(text("""
                    ALTER TABLE campaigns 
                    ADD COLUMN progress INTEGER DEFAULT 0;
                """))
                conn.commit()
                migrations_applied = True
                logger.info("✅ Added 'progress' column")
            
            # Add error_message column if missing
            if 'error_message' not in campaign_columns:
                logger.info("📝 Adding 'error_message' column to campaigns table...")
                conn.execute(text("""
                    ALTER TABLE campaigns 
                    ADD COLUMN error_message TEXT;
                """))
                conn.commit()
                migrations_applied = True
                logger.info("✅ Added 'error_message' column")
            
            if not migrations_applied:
                logger.info("✅ Database schema is up to date")
            else:
                logger.info("✅ Database migration completed successfully")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from app.database.connection import init_db
    
    logger.info("🔄 Running database migrations...")
    init_db()
    success = migrate_database()
    
    if success:
        logger.info("✅ Migration complete")
    else:
        logger.error("❌ Migration failed")
