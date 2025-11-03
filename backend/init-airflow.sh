#!/bin/bash
set -e

# Initialize the Airflow database
airflow db migrate

# Create admin user if it doesn't exist
airflow users create \
    --username "${_AIRFLOW_WWW_USER_USERNAME:-admin}" \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password "${_AIRFLOW_WWW_USER_PASSWORD:-admin}" || true

echo "Airflow initialized successfully"
