#!/usr/bin/env python3
"""
Cleanup script to delete all campaigns (and their related creatives) from the database.
This gives a fresh start for testing the new Creative workflow.
"""

import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.models import Campaign, Creative

# Get database URL from environment or use default
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:2aBSiPNqD8QcepjyW4BKAu4si@adgen-video-db.crws0amqe1e3.us-east-1.rds.amazonaws.com:5432/postgres?sslmode=disable'
)

def cleanup_all_campaigns():
    """Delete all campaigns and their related creatives from the database."""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        print("=" * 80)
        print("Campaign Cleanup Utility")
        print("=" * 80)

        # Count existing campaigns and creatives
        campaign_count = db.query(Campaign).count()
        creative_count = db.query(Creative).count()

        print(f"\nCurrent state:")
        print(f"  Campaigns: {campaign_count}")
        print(f"  Creatives: {creative_count}")

        if campaign_count == 0 and creative_count == 0:
            print("\n✅ Database is already clean. No campaigns or creatives to delete.")
            return

        # Delete all creatives first (due to foreign key constraints)
        print(f"\nDeleting {creative_count} creative(s)...")
        deleted_creatives = db.query(Creative).delete()
        print(f"  ✅ Deleted {deleted_creatives} creative(s)")

        # Delete all campaigns
        print(f"\nDeleting {campaign_count} campaign(s)...")
        deleted_campaigns = db.query(Campaign).delete()
        print(f"  ✅ Deleted {deleted_campaigns} campaign(s)")

        # Commit the changes
        db.commit()

        print("\n" + "=" * 80)
        print("✅ Cleanup Complete!")
        print("=" * 80)
        print("\nDatabase is now clean and ready for testing the new Creative workflow.")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error during cleanup: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    cleanup_all_campaigns()
