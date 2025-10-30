# Quick Start: Production Deployment

Get your Tee Time Finder application running in production in under 15 minutes.

---

## Prerequisites

- Server with Docker & Docker Compose installed
- Domain name (optional)
- Gmail account for notifications

---

## Step 1: Clone and Configure (5 minutes)

```bash
# Clone repository
git clone <your-repo-url>
cd find_tee_time

# Create production environment file
cp .env.production.example .env.production

# Generate JWT secret
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
# Copy output and paste into .env.production as JWT_SECRET_KEY

# Edit environment file
nano .env.production
```

**Required changes in `.env.production`:**

```bash
# 1. Set strong passwords
POSTGRES_PASSWORD=your_strong_password_here
_AIRFLOW_WWW_USER_PASSWORD=your_admin_password_here

# 2. Paste JWT secret from above
JWT_SECRET_KEY=<paste-generated-key-here>

# 3. Set your domain (or use IP address)
PRODUCTION_FRONTEND_URL=http://your-server-ip:3000
REACT_APP_API_URL=http://your-server-ip:8000

# 4. Gmail settings (get App Password from https://myaccount.google.com/apppasswords)
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_gmail_app_password
FROM_EMAIL=your_email@gmail.com

# 5. Golf course credentials
GOLF_USERNAME=your_golf_username
GOLF_PASSWORD=your_golf_password
```

Save and exit (`Ctrl+X`, `Y`, `Enter`).

---

## Step 2: Deploy (5 minutes)

```bash
# Set Airflow UID
echo "AIRFLOW_UID=$(id -u)" >> .env.production

# Create required directories
mkdir -p backend/logs backend/plugins
chmod -R 777 backend/logs backend/plugins

# Secure environment file
chmod 600 .env.production

# Build and start all services
docker-compose -f docker-compose.prod.yml --env-file .env.production build
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d

# Monitor startup (Ctrl+C to exit)
docker-compose -f docker-compose.prod.yml logs -f
```

Wait for all services to be healthy (~2-3 minutes).

---

## Step 3: Configure Airflow (3 minutes)

1. **Access Airflow UI:**
   ```
   http://your-server-ip:8081
   ```

2. **Login:**
   - Username: `admin` (or value from `_AIRFLOW_WWW_USER_USERNAME`)
   - Password: Value from `_AIRFLOW_WWW_USER_PASSWORD` in `.env.production`

3. **Add Variables (Admin → Variables → +):**

   | Key | Value |
   |-----|-------|
   | `golf_username` | Your golf booking username |
   | `golf_password` | Your golf booking password |
   | `kafka_bootstrap_servers` | `kafka:29092` |

4. **Enable DAG:**
   - Go to **DAGs** tab
   - Find `tee_time_checker_dag`
   - Toggle switch to **ON**

5. **Test DAG:**
   - Click **▶ Trigger DAG**
   - Wait 1-2 minutes
   - Check if run succeeded (green circle)

---

## Step 4: Verify (2 minutes)

```bash
# Check all services are running
docker-compose -f docker-compose.prod.yml ps

# Expected output: All services show "Up" or "healthy"

# Test backend
curl http://localhost:8000/

# Test frontend (in browser)
http://your-server-ip:3000

# Check notifier is finding tee times
docker logs tee-time-notifier-prod --tail 20
# Should see: "Found X available tee times"
```

---

## Step 5: Test End-to-End

1. **Open frontend:**
   ```
   http://your-server-ip:3000
   ```

2. **Register account:**
   - Click "Register"
   - Fill in details
   - Submit

3. **Create search:**
   - Login with new account
   - Go to "Find Tee Times"
   - Select course, date, and preferences
   - Click "Start Search"

4. **Verify notification:**
   - Check your email
   - You should receive notification with matching tee times
   - If no tee times available, check logs:
     ```bash
     docker logs tee-time-notifier-prod -f
     ```

---

## Common Issues

### "Port already in use"
```bash
# Find what's using the port
sudo lsof -i :8000

# Stop conflicting service or change port in .env.production
```

### "No tee times found"
```bash
# Check if tee times are being saved to database
docker exec postgres-prod psql -U airflow -d app -c "SELECT COUNT(*) FROM tee_times;"

# Check Airflow DAG logs
docker logs airflow-scheduler-prod --tail 100
```

### "Email not sending"
```bash
# Verify SMTP settings
docker exec tee-time-notifier-prod env | grep SMTP

# Check notifier logs
docker logs tee-time-notifier-prod --tail 50
```

### "Services keep restarting"
```bash
# Check logs for errors
docker-compose -f docker-compose.prod.yml logs

# Check memory
free -h

# If low on memory, reduce Airflow workers or use swap
```

---

## Useful Commands

```bash
# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Restart all services
docker-compose -f docker-compose.prod.yml restart

# Stop all services
docker-compose -f docker-compose.prod.yml stop

# Start all services
docker-compose -f docker-compose.prod.yml start

# Update and rebuild
docker-compose -f docker-compose.prod.yml up -d --build

# Backup database
docker exec postgres-prod pg_dump -U airflow app | gzip > backup.sql.gz
```

---

## Next Steps

1. **Set up SSL/TLS** for production (Let's Encrypt)
2. **Configure reverse proxy** (Nginx/Traefik)
3. **Set up monitoring** (logs, alerts)
4. **Enable automated backups** (cron jobs)
5. **Review security settings**

See [DEPLOYMENT.md](DEPLOYMENT.md) for comprehensive production setup.

---

## Getting Help

- Check [DEPLOYMENT.md](DEPLOYMENT.md) for detailed documentation
- Review [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
- Check service logs for error messages
- Verify all environment variables are set correctly

---

**You're now running in production!** 🎉

Access your application at: `http://your-server-ip:3000`
