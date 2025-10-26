"""
Migration script to add is_available column to tee_times table
Run this before deploying the updated DAG
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://airflow:airflow@postgres/airflow')

def run_migration():
    """Add is_available column to tee_times table"""
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # Start a transaction
        trans = conn.begin()
        try:
            # Check if column already exists
            check_column = text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='tee_times' AND column_name='is_available';
            """)
            result = conn.execute(check_column)

            if result.fetchone():
                print("Column 'is_available' already exists. Skipping migration.")
            else:
                print("Adding 'is_available' column to tee_times table...")

                # Add the column with default value
                add_column = text("""
                    ALTER TABLE tee_times
                    ADD COLUMN is_available BOOLEAN DEFAULT TRUE;
                """)
                conn.execute(add_column)

                # Update existing records to set is_available = TRUE
                update_existing = text("""
                    UPDATE tee_times
                    SET is_available = TRUE
                    WHERE is_available IS NULL;
                """)
                conn.execute(update_existing)

                print("Successfully added 'is_available' column and set all existing records to TRUE")

            trans.commit()
            print("Migration completed successfully!")

        except Exception as e:
            trans.rollback()
            print(f"Migration failed: {e}")
            raise

if __name__ == "__main__":
    run_migration()
