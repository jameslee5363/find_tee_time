#!/bin/bash

# Docker-based migration script for tee_times database
# This runs the migration inside the Docker container

set -e  # Exit on error

echo "=========================================="
echo "Running Database Migration (Docker)"
echo "Adding is_available column to tee_times"
echo "=========================================="

# Navigate to backend directory
cd /Users/jameslee/Desktop/find_tee_time/backend

# Check if docker-compose is running
if ! docker-compose -f docker-compose.app.yml ps postgres | grep -q "Up"; then
    echo "ERROR: PostgreSQL container is not running"
    echo "Please start your docker-compose stack first:"
    echo "  cd /Users/jameslee/Desktop/find_tee_time/backend"
    echo "  docker-compose -f docker-compose.app.yml up -d postgres"
    exit 1
fi

echo "PostgreSQL container is running. Proceeding with migration..."
echo ""

# Option 1: Run SQL migration directly via psql
echo "Running SQL migration via psql..."
docker-compose -f docker-compose.app.yml exec -T postgres psql -U airflow -d airflow < migrations/add_is_available_column.sql

echo ""
echo "=========================================="
echo "Migration completed successfully!"
echo "=========================================="
echo ""
echo "You can now restart your Airflow services to use the updated DAG:"
echo "  docker-compose -f docker-compose.app.yml restart"
