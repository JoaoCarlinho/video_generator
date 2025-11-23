"""Quick script to verify the database schema."""

import sys
from pathlib import Path

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, inspect
from sqlalchemy.pool import NullPool
from app.config import settings

# Create engine
db_url = settings.database_url
if '?' in db_url:
    db_url += '&sslmode=require'
else:
    db_url += '?sslmode=require'

engine = create_engine(db_url, poolclass=NullPool, echo=False)
inspector = inspect(engine)

print("\n" + "=" * 80)
print("DATABASE SCHEMA VERIFICATION")
print("=" * 80)

# Show all tables
print("\n📋 Tables in public schema:")
for table in inspector.get_table_names():
    print(f"  ✓ {table}")

    # Show columns
    columns = inspector.get_columns(table)
    print(f"    Columns ({len(columns)}):")
    for col in columns:
        nullable = "NULL" if col['nullable'] else "NOT NULL"
        print(f"      - {col['name']}: {col['type']} ({nullable})")

    # Show foreign keys
    fks = inspector.get_foreign_keys(table)
    if fks:
        print(f"    Foreign Keys ({len(fks)}):")
        for fk in fks:
            print(f"      - {fk['constrained_columns'][0]} → "
                  f"{fk['referred_table']}.{fk['referred_columns'][0]} "
                  f"(ondelete={fk.get('ondelete', 'NO ACTION')})")
    print()

print("=" * 80)
print("✅ Schema verification complete!")
print("=" * 80)
