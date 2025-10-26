-- Migration: Add is_available column to tee_times table
-- Run this SQL script against your database before deploying the updated DAG

-- Check if column exists and add it if it doesn't
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'tee_times'
        AND column_name = 'is_available'
    ) THEN
        -- Add the column with default value TRUE
        ALTER TABLE tee_times
        ADD COLUMN is_available BOOLEAN DEFAULT TRUE;

        -- Update existing records to ensure they have is_available = TRUE
        UPDATE tee_times
        SET is_available = TRUE
        WHERE is_available IS NULL;

        RAISE NOTICE 'Column is_available added successfully to tee_times table';
    ELSE
        RAISE NOTICE 'Column is_available already exists in tee_times table';
    END IF;
END $$;
