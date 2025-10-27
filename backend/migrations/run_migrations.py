"""
Run database migrations for the tee time finder application.
"""
import psycopg2
import os
from pathlib import Path

# Database connection parameters
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': os.getenv('POSTGRES_PORT', '5432'),
    'database': os.getenv('POSTGRES_DB', 'airflow'),
    'user': os.getenv('POSTGRES_USER', 'airflow'),
    'password': os.getenv('POSTGRES_PASSWORD', 'airflow')
}

def run_migration(sql_file: str):
    """Execute a SQL migration file."""
    print(f"Running migration: {sql_file}")

    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Read and execute SQL file
        migration_path = Path(__file__).parent / sql_file
        with open(migration_path, 'r') as f:
            sql = f.read()
            cursor.execute(sql)

        # Commit changes
        conn.commit()
        print(f"✓ Successfully applied migration: {sql_file}")

        # Close connection
        cursor.close()
        conn.close()

    except Exception as e:
        print(f"✗ Error applying migration {sql_file}: {e}")
        raise

def main():
    """Run all migrations."""
    migrations = [
        'create_users_table.sql',
        'create_tee_time_searches_table.sql',
        'create_tee_time_notifications_table.sql',
    ]

    print("Starting database migrations...")
    print(f"Database: {DB_CONFIG['database']} at {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print("-" * 50)

    for migration in migrations:
        run_migration(migration)

    print("-" * 50)
    print("All migrations completed successfully!")

if __name__ == '__main__':
    main()
