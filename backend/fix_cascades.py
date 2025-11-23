"""Fix foreign key CASCADE constraints."""

import sys
from pathlib import Path

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.pool import NullPool
from app.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create engine
db_url = settings.database_url
if '?' in db_url:
    db_url += '&sslmode=require'
else:
    db_url += '?sslmode=require'

engine = create_engine(db_url, poolclass=NullPool, echo=False)

print("\n" + "=" * 80)
print("FIXING CASCADE DELETE CONSTRAINTS")
print("=" * 80 + "\n")

with engine.begin() as conn:
    # Fix products.brand_id FK
    logger.info("Fixing products.brand_id → brands.id CASCADE...")
    conn.execute(text("""
        ALTER TABLE products
        DROP CONSTRAINT IF EXISTS products_brand_id_fkey CASCADE
    """))
    conn.execute(text("""
        ALTER TABLE products
        ADD CONSTRAINT products_brand_id_fkey
        FOREIGN KEY (brand_id)
        REFERENCES brands(id)
        ON DELETE CASCADE
    """))
    logger.info("  ✓ products.brand_id CASCADE fixed")

    # Fix campaigns.product_id FK
    logger.info("Fixing campaigns.product_id → products.id CASCADE...")
    conn.execute(text("""
        ALTER TABLE campaigns
        DROP CONSTRAINT IF EXISTS campaigns_product_id_fkey CASCADE
    """))
    conn.execute(text("""
        ALTER TABLE campaigns
        ADD CONSTRAINT campaigns_product_id_fkey
        FOREIGN KEY (product_id)
        REFERENCES products(id)
        ON DELETE CASCADE
    """))
    logger.info("  ✓ campaigns.product_id CASCADE fixed")

    # Fix creatives.campaign_id FK
    logger.info("Fixing creatives.campaign_id → campaigns.id CASCADE...")
    conn.execute(text("""
        ALTER TABLE creatives
        DROP CONSTRAINT IF EXISTS creatives_campaign_id_fkey CASCADE
    """))
    conn.execute(text("""
        ALTER TABLE creatives
        ADD CONSTRAINT creatives_campaign_id_fkey
        FOREIGN KEY (campaign_id)
        REFERENCES campaigns(id)
        ON DELETE CASCADE
    """))
    logger.info("  ✓ creatives.campaign_id CASCADE fixed")

print("\n" + "=" * 80)
print("✅ All CASCADE constraints fixed!")
print("=" * 80)

# Verify
print("\nVerifying constraints...")
inspector = inspect(engine)

for table, fk_col, ref_table in [
    ('products', 'brand_id', 'brands'),
    ('campaigns', 'product_id', 'products'),
    ('creatives', 'campaign_id', 'campaigns')
]:
    fks = inspector.get_foreign_keys(table)
    fk = next((f for f in fks if fk_col in f['constrained_columns']), None)
    if fk:
        ondelete = fk.get('ondelete', 'NO ACTION')
        status = "✓" if ondelete == "CASCADE" else "✗"
        print(f"  {status} {table}.{fk_col} → {ref_table}.id (ondelete={ondelete})")

print("\n✅ Done!\n")
