#!/bin/bash

# Migration script runner for tee_times database
# This script will add the is_available column to the tee_times table

set -e  # Exit on error

echo "=========================================="
echo "Running Database Migration"
echo "Adding is_available column to tee_times"
echo "=========================================="

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL environment variable is not set"
    echo "Please set it to your PostgreSQL connection string"
    echo "Example: export DATABASE_URL='postgresql://airflow:airflow@localhost:5432/airflow'"
    exit 1
fi

echo "Database URL: $DATABASE_URL"
echo ""

# Option 1: Run via Python script
echo "Running migration via Python script..."
cd /Users/jameslee/Desktop/find_tee_time/backend
python migrations/add_is_available_column.py

echo ""
echo "=========================================="
echo "Migration completed successfully!"
echo "=========================================="
