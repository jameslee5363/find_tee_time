# Database Migrations

This directory contains database migration scripts for the Find Tee Time application.

## Current Migration: Add `is_available` Column

This migration adds an `is_available` column to the `tee_times` table to track whether tee times are currently available or have been booked/removed.

### Why This Migration Is Needed

The updated DAG now:
1. Tracks tee times that disappear from the API (fully booked or removed)
2. Marks them as `is_available = FALSE` instead of leaving them in the database unchanged
3. Updates `available_spots` when they change
4. Ensures the database always reflects the current state of tee time availability

### Running the Migration

#### Option 1: Automatic Migration (Recommended for Docker)

The DAG now includes automatic schema checking. The migration will run automatically on the next DAG execution if the column doesn't exist.

**Simply restart your Airflow services:**

```bash
cd /Users/jameslee/Desktop/find_tee_time/backend
docker-compose -f docker-compose.app.yml restart
```

The next time the `save_to_database` task runs, it will automatically add the column.

#### Option 2: Manual Migration via Docker (Safest)

If you prefer to run the migration manually before the DAG runs:

```bash
cd /Users/jameslee/Desktop/find_tee_time/backend
./run_migration_docker.sh
```

This will:
1. Check if PostgreSQL container is running
2. Run the SQL migration script
3. Add the `is_available` column with default value `TRUE`
4. Set all existing records to `is_available = TRUE`

#### Option 3: Direct SQL Execution

Connect to your PostgreSQL database and run:

```bash
cd /Users/jameslee/Desktop/find_tee_time/backend
docker-compose -f docker-compose.app.yml exec postgres psql -U airflow -d airflow -f /path/to/add_is_available_column.sql
```

Or copy and paste the SQL from [add_is_available_column.sql](add_is_available_column.sql) directly into your PostgreSQL client.

#### Option 4: Python Migration Script

If running outside Docker:

```bash
cd /Users/jameslee/Desktop/find_tee_time/backend
export DATABASE_URL='postgresql://airflow:airflow@localhost:5432/airflow'
./run_migration.sh
```

### Verifying the Migration

After running the migration, verify it was successful:

```bash
docker-compose -f docker-compose.app.yml exec postgres psql -U airflow -d airflow -c "\d tee_times"
```

You should see the `is_available` column in the table schema.

### Migration SQL

```sql
-- Add is_available column
ALTER TABLE tee_times
ADD COLUMN is_available BOOLEAN DEFAULT TRUE;

-- Update existing records
UPDATE tee_times
SET is_available = TRUE
WHERE is_available IS NULL;
```

## Rollback (if needed)

If you need to rollback this migration:

```sql
ALTER TABLE tee_times DROP COLUMN is_available;
```

**Warning:** Only rollback if you also revert the DAG code changes, otherwise the DAG will fail.

## Future Migrations

When creating new migrations:
1. Create both a `.py` and `.sql` version
2. Add a check for existing schema before altering
3. Update this README with instructions
4. Test in a development environment first
5. Consider adding the migration to the DAG's `ensure_database_schema()` function for automatic execution
