#!/usr/bin/env python3
"""
Run database migrations for the video generator backend.

This script applies SQL migrations to the PostgreSQL database.
It replaces Supabase auth with direct PostgreSQL authentication.

Usage:
    python run_migration.py

Environment Variables:
    DATABASE_URL: PostgreSQL connection string
"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

import psycopg2
from psycopg2.extras import RealDictCursor


def get_database_url():
    """Get database URL from environment or use default."""
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url

    # Default to local development or terraform values
    db_host = os.getenv("DB_HOST", "adgen-video-db.crws0amqe1e3.us-east-1.rds.amazonaws.com")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "postgres")
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "2aBSiPNqD8QcepjyW4BKAu4si")

    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


def run_migration(migration_file: str):
    """Run a SQL migration file."""
    db_url = get_database_url()
    print(f"Connecting to database...")

    # Parse connection string
    # Format: postgresql://user:password@host:port/database
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        print(f"Connected successfully!")
        print(f"Running migration: {migration_file}")

        # Read and execute migration
        migration_path = Path(__file__).parent / "migrations" / migration_file
        if not migration_path.exists():
            print(f"Error: Migration file not found: {migration_path}")
            return False

        with open(migration_path, "r") as f:
            sql = f.read()

        cursor.execute(sql)
        print(f"Migration completed successfully!")

        # Verify users table exists
        cursor.execute("SELECT COUNT(*) as count FROM users")
        result = cursor.fetchone()
        print(f"Users table has {result['count']} records")

        cursor.close()
        conn.close()
        return True

    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    """Run all pending migrations."""
    print("=" * 60)
    print("  Database Migration: Replace Supabase with Direct Auth")
    print("=" * 60)
    print()

    # Run the users table migration
    success = run_migration("001_create_users_table.sql")

    print()
    if success:
        print("=" * 60)
        print("  Migration Complete!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("  1. Rebuild and deploy the backend")
        print("  2. Rebuild and deploy the frontend")
        print("  3. Test login/signup at your frontend URL")
        print()
    else:
        print("=" * 60)
        print("  Migration Failed!")
        print("=" * 60)
        print()
        print("Check the error messages above and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
