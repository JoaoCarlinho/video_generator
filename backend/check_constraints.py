"""Check actual foreign key constraints in database."""

import sys
from pathlib import Path

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from app.config import settings

# Create engine
db_url = settings.database_url
if '?' in db_url:
    db_url += '&sslmode=require'
else:
    db_url += '?sslmode=require'

engine = create_engine(db_url, poolclass=NullPool, echo=False)

print("\n" + "=" * 80)
print("CHECKING FOREIGN KEY CONSTRAINTS (Direct SQL Query)")
print("=" * 80 + "\n")

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT
            tc.table_name,
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name,
            rc.delete_rule
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        JOIN information_schema.referential_constraints AS rc
            ON rc.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema = 'public'
        ORDER BY tc.table_name, kcu.column_name;
    """))

    print("Foreign Key Constraints:\n")
    for row in result:
        table, column, ref_table, ref_column, delete_rule = row
        status = "✓" if delete_rule == "CASCADE" else "✗"
        print(f"{status} {table}.{column} → {ref_table}.{ref_column}")
        print(f"   ON DELETE {delete_rule}\n")

print("=" * 80)
