# Migration Files Removed

All Alembic migration files have been deleted as part of the database reset.

## Why?

The campaign had accumulated migration files with conflicts (duplicate revision IDs) and the schema needed a fresh start.

## New Approach

Database schema is now managed through SQL scripts located in `backend/scripts/`:

- **`reset_database.sql`** - Drops all tables
- **`create_schema.sql`** - Creates complete schema from scratch
- **`DATABASE_RESET_GUIDE.md`** - Step-by-step instructions

## What This Means

- No more Alembic migrations needed for this project
- Schema changes are made by updating the SQL scripts
- Cleaner, more straightforward database management
- Perfect for small to medium projects with Supabase

## If You Need Migrations in the Future

If the project grows and you need proper migration management:

1. Restore Alembic by creating an initial migration:
   ```bash
   cd backend
   alembic revision --autogenerate -m "initial_schema"
   ```

2. Review and edit the generated migration file

3. Apply it:
   ```bash
   alembic upgrade head
   ```

But for now, use the SQL scripts approach - it's simpler and sufficient for this project's needs.
