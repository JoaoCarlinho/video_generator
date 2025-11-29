#!/usr/bin/env python3
"""Delete all records from all tables in the database."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.database import connection as db_connection
from app.database.connection import init_db
from app.database.models import Brand, Product, Campaign, Creative


def main():
    """Delete all records from all tables."""
    init_db()

    if db_connection.SessionLocal is None:
        print("Error: Database connection not initialized properly.")
        print("Check your DATABASE_URL in .env file.")
        return

    db = db_connection.SessionLocal()

    try:
        # Count records in each table
        brand_count = db.query(Brand).count()
        product_count = db.query(Product).count()
        campaign_count = db.query(Campaign).count()
        creative_count = db.query(Creative).count()

        total = brand_count + product_count + campaign_count + creative_count

        print("\n" + "=" * 80)
        print("📊 Current Database Records:")
        print("=" * 80)
        print(f"  Brands:    {brand_count}")
        print(f"  Products:  {product_count}")
        print(f"  Campaigns: {campaign_count}")
        print(f"  Creatives: {creative_count}")
        print(f"  ─────────────────────")
        print(f"  Total:     {total}")
        print("=" * 80)

        if total == 0:
            print("\n✅ Database is already empty.")
            return

        # Delete all records (cascade will handle related records)
        # Delete from parent table (brands) - cascade will delete products, campaigns, creatives
        print("\n🗑️  Deleting all records...")

        # Delete creatives first (no dependencies)
        creative_deleted = db.query(Creative).delete()
        print(f"  ✓ Deleted {creative_deleted} creatives")

        # Delete campaigns (depends on products)
        campaign_deleted = db.query(Campaign).delete()
        print(f"  ✓ Deleted {campaign_deleted} campaigns")

        # Delete products (depends on brands)
        product_deleted = db.query(Product).delete()
        print(f"  ✓ Deleted {product_deleted} products")

        # Delete brands (parent table)
        brand_deleted = db.query(Brand).delete()
        print(f"  ✓ Deleted {brand_deleted} brands")

        db.commit()

        print("\n" + "=" * 80)
        print("✅ Successfully deleted all records from database!")
        print("=" * 80 + "\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
