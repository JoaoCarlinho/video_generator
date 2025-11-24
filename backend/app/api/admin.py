"""
Admin API endpoints for database maintenance.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from sqlalchemy import text, inspect
import logging

from app.database.connection import get_db, engine
from app.database.models import Campaign, Creative
from app.api.auth import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter()


@router.delete(
    "/cleanup/campaigns",
    summary="Delete all campaigns",
    description="Delete all campaigns and creatives from the database (admin only)"
)
async def cleanup_all_campaigns(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Delete all campaigns and their related creatives from the database.

    **WARNING**: This will delete ALL campaigns and creatives for ALL users.
    Use with caution!

    **Returns:**
    - Statistics about deleted records
    """
    try:
        # Count existing records
        campaign_count = db.query(Campaign).count()
        creative_count = db.query(Creative).count()

        logger.info(f"Starting cleanup: {campaign_count} campaigns, {creative_count} creatives")

        if campaign_count == 0 and creative_count == 0:
            return {
                "status": "success",
                "message": "Database is already clean",
                "deleted_campaigns": 0,
                "deleted_creatives": 0
            }

        # Delete all creatives first (due to foreign key constraints)
        deleted_creatives = db.query(Creative).delete()
        logger.info(f"Deleted {deleted_creatives} creatives")

        # Delete all campaigns
        deleted_campaigns = db.query(Campaign).delete()
        logger.info(f"Deleted {deleted_campaigns} campaigns")

        # Commit the changes
        db.commit()

        logger.info("✅ Cleanup complete")

        return {
            "status": "success",
            "message": "Cleanup completed successfully",
            "deleted_campaigns": deleted_campaigns,
            "deleted_creatives": deleted_creatives
        }

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Cleanup failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cleanup failed: {str(e)}"
        )


@router.get(
    "/stats/campaigns",
    summary="Get campaign statistics",
    description="Get counts of campaigns and creatives"
)
async def get_campaign_stats(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> Dict[str, int]:
    """
    Get statistics about campaigns and creatives in the database.

    **Returns:**
    - Campaign and creative counts
    """
    try:
        campaign_count = db.query(Campaign).count()
        creative_count = db.query(Creative).count()

        return {
            "total_campaigns": campaign_count,
            "total_creatives": creative_count
        }

    except Exception as e:
        logger.error(f"❌ Failed to get stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {str(e)}"
        )


@router.post(
    "/migrate/schema",
    summary="Run database schema migrations",
    description="Add missing columns to existing tables (non-destructive)"
)
async def migrate_schema(
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """
    Run database schema migrations to add missing columns.

    This is a **non-destructive** operation that only adds missing columns.
    Existing data is preserved.

    **Returns:**
    - Migration status and list of applied migrations
    """
    if engine is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database engine not available"
        )

    try:
        migrations_applied: List[str] = []

        with engine.connect() as conn:
            # Check existing columns in campaigns table
            inspector = inspect(engine)

            try:
                campaign_columns = [col['name'] for col in inspector.get_columns('campaigns')]
            except Exception as e:
                logger.error(f"Failed to inspect campaigns table: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Could not inspect campaigns table: {str(e)}"
                )

            # Migration 1: Add progress column
            if 'progress' not in campaign_columns:
                logger.info("📝 Adding 'progress' column to campaigns table...")
                conn.execute(text("""
                    ALTER TABLE campaigns
                    ADD COLUMN progress INTEGER DEFAULT 0;
                """))
                conn.commit()
                migrations_applied.append("Added 'progress' column to campaigns")
                logger.info("✅ Added 'progress' column")

            # Migration 2: Add error_message column
            if 'error_message' not in campaign_columns:
                logger.info("📝 Adding 'error_message' column to campaigns table...")
                conn.execute(text("""
                    ALTER TABLE campaigns
                    ADD COLUMN error_message TEXT;
                """))
                conn.commit()
                migrations_applied.append("Added 'error_message' column to campaigns")
                logger.info("✅ Added 'error_message' column")

        if not migrations_applied:
            return {
                "status": "success",
                "message": "Database schema is already up to date",
                "migrations_applied": []
            }

        return {
            "status": "success",
            "message": f"Applied {len(migrations_applied)} migration(s)",
            "migrations_applied": migrations_applied
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Migration failed: {str(e)}"
        )
