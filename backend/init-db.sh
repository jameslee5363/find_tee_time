#!/bin/bash
set -e

# Create the 'app' database if it doesn't exist
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    SELECT 'CREATE DATABASE app'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'app')\gexec
EOSQL

echo "Database 'app' created successfully"
