# Production Deployment Guide

This guide will walk you through deploying the Tee Time Finder application to production.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Security Configuration](#security-configuration)
4. [Deployment Steps](#deployment-steps)
5. [Post-Deployment Configuration](#post-deployment-configuration)
6. [Monitoring and Logs](#monitoring-and-logs)
7. [Troubleshooting](#troubleshooting)
8. [Updating the Application](#updating-the-application)

---

## Prerequisites

Before deploying, ensure you have:

- **Docker** (version 20.10 or higher)
- **Docker Compose** (version 2.0 or higher)
- A server with at least:
  - 4GB RAM
  - 20GB disk space
  - Ubuntu 20.04+ / Debian 11+ / similar Linux distribution
- Domain name (optional but recommended)
- SSL certificate (for HTTPS - recommended)

### Check Prerequisites

```bash
docker --version
docker-compose --version
```

---

## Environment Setup

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd find_tee_time
```

### 2. Create Production Environment File

```bash
# Copy the production example file
cp .env.production.example .env.production

# Edit with your actual values
nano .env.production  # or use vim, vi, etc.
```

### 3. Configure Environment Variables

Open `.env.production` and update these **CRITICAL** values:

#### Database Security
```bash
POSTGRES_PASSWORD=YOUR_STRONG_PASSWORD_HERE
```

#### JWT Security
Generate a strong secret key:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```
Copy the output to:
```bash
JWT_SECRET_KEY=<paste-generated-key-here>
```

#### Airflow Admin
```bash
_AIRFLOW_WWW_USER_USERNAME=admin
_AIRFLOW_WWW_USER_PASSWORD=YOUR_STRONG_PASSWORD_HERE
```

#### Frontend/Backend URLs
```bash
# Your production frontend URL
PRODUCTION_FRONTEND_URL=https://yourdomain.com

# Your production backend API URL
REACT_APP_API_URL=https://api.yourdomain.com
```

#### Email Configuration (Gmail Example)
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_specific_password  # NOT your regular password!
FROM_EMAIL=your_email@gmail.com
```

**For Gmail**: Generate an App Password at https://myaccount.google.com/apppasswords

#### Golf Course Credentials
```bash
GOLF_USERNAME=your_golf_booking_username
GOLF_PASSWORD=your_golf_booking_password
```

---

## Security Configuration

### 1. File Permissions

Secure your environment file:
```bash
chmod 600 .env.production
```

### 2. Firewall Configuration

If using UFW (Ubuntu):
```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP (if not using reverse proxy)
sudo ufw allow 3000/tcp  # Frontend
sudo ufw allow 8000/tcp  # Backend API
sudo ufw allow 8081/tcp  # Airflow (optional - can be internal only)

# Enable firewall
sudo ufw enable
```

### 3. Reverse Proxy (Recommended)

For production, use Nginx or Traefik as a reverse proxy with SSL/TLS.

Example Nginx configuration:
```nginx
# /etc/nginx/sites-available/tee-time-finder

# Backend API
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Frontend
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Enable with:
```bash
sudo ln -s /etc/nginx/sites-available/tee-time-finder /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 4. SSL/TLS (Let's Encrypt)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificates
sudo certbot --nginx -d yourdomain.com -d api.yourdomain.com

# Auto-renewal (certbot does this automatically)
sudo certbot renew --dry-run
```

---

## Deployment Steps

### 1. Set Airflow UID

```bash
# Create .env file with Airflow UID
echo "AIRFLOW_UID=$(id -u)" >> .env.production
```

### 2. Create Required Directories

```bash
# Create directories for Airflow logs and DAGs
mkdir -p backend/logs backend/plugins

# Set permissions
chmod -R 777 backend/logs backend/plugins
```

### 3. Build and Start Services

```bash
# Build all services
docker-compose -f docker-compose.prod.yml --env-file .env.production build

# Start all services in detached mode
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d
```

### 4. Verify Services Are Running

```bash
# Check all containers
docker-compose -f docker-compose.prod.yml ps

# Expected output (all should be "Up" or "healthy"):
# - postgres-prod
# - kafka-prod
# - airflow-init-prod (Exited with code 0 is OK)
# - airflow-webserver-prod
# - airflow-scheduler-prod
# - fastapi-backend-prod
# - tee-time-notifier-prod
# - react-frontend-prod
```

### 5. Monitor Startup Logs

```bash
# Watch logs from all services
docker-compose -f docker-compose.prod.yml --env-file .env.production logs -f

# Check specific service
docker logs fastapi-backend-prod -f
docker logs tee-time-notifier-prod -f
docker logs airflow-scheduler-prod -f
```

---

## Post-Deployment Configuration

### 1. Access Airflow UI

Navigate to: `http://your-server-ip:8081`

Login with:
- Username: Value from `_AIRFLOW_WWW_USER_USERNAME` (default: `admin`)
- Password: Value from `_AIRFLOW_WWW_USER_PASSWORD`

### 2. Configure Airflow Variables

In Airflow UI:
1. Go to **Admin** → **Variables**
2. Add these variables:

| Key | Value | Description |
|-----|-------|-------------|
| `golf_username` | Your golf booking username | Golf course login |
| `golf_password` | Your golf booking password | Golf course login |
| `kafka_bootstrap_servers` | `kafka:29092` | Kafka connection |

### 3. Enable DAG

1. In Airflow UI, go to **DAGs**
2. Find `tee_time_checker_dag`
3. Toggle it **ON**
4. Trigger manually to test: Click **▶ Trigger DAG**

### 4. Verify Application

Test each component:

```bash
# Backend API health check
curl http://localhost:8000/

# Frontend (in browser)
http://localhost:3000

# Airflow
http://localhost:8081
```

---

## Monitoring and Logs

### View Logs

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker logs fastapi-backend-prod -f
docker logs tee-time-notifier-prod -f
docker logs airflow-scheduler-prod -f

# Last 100 lines
docker logs fastapi-backend-prod --tail 100
```

### Container Status

```bash
# Check all containers
docker-compose -f docker-compose.prod.yml ps

# Check resource usage
docker stats
```

### Database Inspection

```bash
# Connect to PostgreSQL
docker exec -it postgres-prod psql -U airflow -d app

# Useful queries:
# \dt                          # List tables
# SELECT COUNT(*) FROM tee_times;
# SELECT COUNT(*) FROM tee_time_searches WHERE status='pending';
# SELECT COUNT(*) FROM tee_time_notifications;
```

### Kafka Topics

```bash
# List topics
docker exec -it kafka-prod kafka-topics --bootstrap-server localhost:9092 --list

# Check messages in topic
docker exec -it kafka-prod kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic tee-time-searches \
  --from-beginning \
  --max-messages 10
```

---

## Troubleshooting

### Services Won't Start

```bash
# Check logs for errors
docker-compose -f docker-compose.prod.yml logs

# Restart specific service
docker-compose -f docker-compose.prod.yml restart backend

# Rebuild and restart
docker-compose -f docker-compose.prod.yml up -d --build backend
```

### Port Already in Use

```bash
# Find process using port
sudo lsof -i :8000
sudo lsof -i :9092

# Kill process or change port in .env.production
```

### Database Connection Errors

```bash
# Check database is healthy
docker exec postgres-prod pg_isready -U airflow

# Verify 'app' database exists
docker exec postgres-prod psql -U airflow -c "\l"

# Recreate 'app' database if missing
docker exec postgres-prod psql -U airflow -c "CREATE DATABASE app;"
```

### Airflow DAG Not Running

1. Check DAG is enabled in UI
2. Check scheduler logs:
   ```bash
   docker logs airflow-scheduler-prod --tail 100
   ```
3. Verify DAG file has no syntax errors:
   ```bash
   docker exec airflow-scheduler-prod python /opt/airflow/dags/tee_time_checker_dag.py
   ```

### Notification System Not Sending Emails

```bash
# Check notifier logs
docker logs tee-time-notifier-prod --tail 100

# Verify environment variables
docker exec tee-time-notifier-prod env | grep SMTP
docker exec tee-time-notifier-prod env | grep DATABASE_URL

# Test email manually (in backend container)
docker exec -it fastapi-backend-prod python -c "
from notifications import notification_service
result = notification_service.send_tee_time_notification(
    user_email='test@example.com',
    user_name='Test',
    course_name='Test Course',
    tee_off_date='2025-10-31',
    tee_off_time='10:00',
    available_spots=4,
    group_size=2
)
print(result)
"
```

### Out of Memory

```bash
# Check memory usage
free -h
docker stats

# Restart services to free memory
docker-compose -f docker-compose.prod.yml restart
```

---

## Updating the Application

### Pull Latest Code

```bash
# Stop services
docker-compose -f docker-compose.prod.yml down

# Pull updates
git pull origin main

# Rebuild with no cache
docker-compose -f docker-compose.prod.yml build --no-cache

# Restart
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d
```

### Update Environment Variables Only

```bash
# Edit .env.production
nano .env.production

# Restart affected services
docker-compose -f docker-compose.prod.yml up -d --force-recreate backend tee-time-notifier
```

### Database Migration

```bash
# If database schema changes, run migrations in backend container
docker exec -it fastapi-backend-prod alembic upgrade head
```

---

## Backup and Restore

### Backup Database

```bash
# Backup 'app' database
docker exec postgres-prod pg_dump -U airflow app > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup with compression
docker exec postgres-prod pg_dump -U airflow app | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

### Restore Database

```bash
# Restore from backup
docker exec -i postgres-prod psql -U airflow app < backup_20251030_120000.sql

# Restore from compressed backup
gunzip -c backup_20251030_120000.sql.gz | docker exec -i postgres-prod psql -U airflow app
```

### Backup Volumes

```bash
# Backup Postgres data volume
docker run --rm \
  -v find_tee_time_postgres-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/postgres-data-backup.tar.gz /data

# Backup Kafka data volume
docker run --rm \
  -v find_tee_time_kafka-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/kafka-data-backup.tar.gz /data
```

---

## Shutting Down

### Stop Services

```bash
# Stop all services (keeps data)
docker-compose -f docker-compose.prod.yml stop

# Stop and remove containers (keeps data)
docker-compose -f docker-compose.prod.yml down

# Stop, remove containers AND volumes (DELETES ALL DATA)
docker-compose -f docker-compose.prod.yml down -v
```

---

## Additional Resources

- **Airflow Documentation**: https://airflow.apache.org/docs/
- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **Docker Compose Documentation**: https://docs.docker.com/compose/
- **Kafka Documentation**: https://kafka.apache.org/documentation/

---

## Support

For issues or questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review logs for error messages
3. Check GitHub issues
4. Create a new issue with relevant logs and configuration
