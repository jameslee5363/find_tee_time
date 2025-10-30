# Deployment Guide Overview

This directory contains everything you need to deploy the Tee Time Finder application to production.

---

## 📚 Documentation Files

### Quick Start
- **[QUICKSTART_DEPLOYMENT.md](QUICKSTART_DEPLOYMENT.md)** - Get running in 15 minutes
  - Fastest way to deploy
  - Step-by-step commands
  - Perfect for first-time deployment

### Comprehensive Guide
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete production deployment guide
  - Prerequisites and setup
  - Security configuration
  - SSL/TLS setup
  - Monitoring and troubleshooting
  - Backup and restore procedures

### Checklist
- **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** - Pre/post deployment checklist
  - Ensures nothing is missed
  - Track deployment progress
  - Verify each step completed

---

## 🚀 Which Guide Should I Use?

### First Time Deploying?
→ Start with [QUICKSTART_DEPLOYMENT.md](QUICKSTART_DEPLOYMENT.md)

### Production Deployment with Security?
→ Use [DEPLOYMENT.md](DEPLOYMENT.md) + [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)

### Already Deployed, Need to Update?
→ See "Updating the Application" section in [DEPLOYMENT.md](DEPLOYMENT.md)

---

## 📁 Configuration Files

### Environment Files
- **`.env.example`** - Development environment template
- **`.env.production.example`** - Production environment template (use this!)

### Docker Compose Files
- **`docker-compose.dev.yml`** - Development environment (hot-reload, debugging tools)
- **`docker-compose.prod.yml`** - Production environment (optimized, secure)

---

## ⚡ Quick Deploy Commands

```bash
# 1. Create production environment
cp .env.production.example .env.production
nano .env.production  # Edit with your values

# 2. Deploy
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d

# 3. Monitor
docker-compose -f docker-compose.prod.yml logs -f
```

---

## 🔧 Key Configuration Required

Before deploying, you **must** configure:

1. **JWT Secret** - Generate with:
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(64))"
   ```

2. **Database Password** - Strong password for PostgreSQL

3. **Airflow Admin Password** - For Airflow UI access

4. **Domain URLs** - Frontend and backend URLs

5. **Email SMTP** - Gmail App Password for notifications

6. **Golf Credentials** - Golf course booking system login

See `.env.production.example` for all configuration options.

---

## 🏗️ Architecture

The application consists of:

- **Frontend** (React) - Port 3000
- **Backend API** (FastAPI) - Port 8000
- **Airflow** (Scheduler + Webserver) - Port 8081
- **PostgreSQL** (Database) - Port 5433
- **Kafka** (Message Queue) - Port 9092
- **Tee Time Notifier** (Background service)

All services are containerized and orchestrated with Docker Compose.

---

## 🔒 Security Best Practices

1. ✅ Use strong passwords for all services
2. ✅ Generate unique JWT secret key
3. ✅ Use Gmail App Passwords (not regular password)
4. ✅ Set `chmod 600` on `.env.production`
5. ✅ Use HTTPS in production (SSL/TLS)
6. ✅ Configure firewall to only expose necessary ports
7. ✅ Keep containers updated
8. ✅ Regular database backups

See [DEPLOYMENT.md](DEPLOYMENT.md#security-configuration) for detailed security setup.

---

## 📊 Monitoring

### Check Service Status
```bash
docker-compose -f docker-compose.prod.yml ps
```

### View Logs
```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker logs fastapi-backend-prod -f
docker logs tee-time-notifier-prod -f
```

### Database Queries
```bash
docker exec postgres-prod psql -U airflow -d app -c "SELECT COUNT(*) FROM tee_times;"
```

---

## 🔄 Common Operations

### Start Services
```bash
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d
```

### Stop Services
```bash
docker-compose -f docker-compose.prod.yml stop
```

### Restart Services
```bash
docker-compose -f docker-compose.prod.yml restart
```

### Update Application
```bash
git pull origin main
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

### Backup Database
```bash
docker exec postgres-prod pg_dump -U airflow app | gzip > backup_$(date +%Y%m%d).sql.gz
```

### View Resource Usage
```bash
docker stats
```

---

## 🆘 Troubleshooting

### Services Won't Start
- Check logs: `docker-compose -f docker-compose.prod.yml logs`
- Verify environment variables in `.env.production`
- Ensure ports aren't already in use
- Check disk space: `df -h`

### No Tee Times Found
- Check Airflow DAG is enabled and running
- Verify golf credentials are correct
- Check scheduler logs: `docker logs airflow-scheduler-prod`

### Email Notifications Not Sending
- Verify SMTP credentials
- Ensure Gmail App Password is used (not regular password)
- Check notifier logs: `docker logs tee-time-notifier-prod`

### Database Connection Errors
- Ensure PostgreSQL is healthy: `docker ps`
- Check DATABASE_URL is correct
- Verify 'app' database exists

See [DEPLOYMENT.md](DEPLOYMENT.md#troubleshooting) for comprehensive troubleshooting.

---

## 📞 Support

For issues or questions:

1. Check the troubleshooting section in [DEPLOYMENT.md](DEPLOYMENT.md)
2. Review service logs for error messages
3. Verify all configuration in `.env.production`
4. Check [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) for missed steps

---

## 📝 Deployment Workflow Summary

```
1. Server Setup
   ↓
2. Clone Repository
   ↓
3. Create .env.production (from template)
   ↓
4. Configure all required variables
   ↓
5. Build & start services
   ↓
6. Configure Airflow (UI)
   ↓
7. Enable DAG
   ↓
8. Verify all services
   ↓
9. Test end-to-end
   ↓
10. Monitor & maintain
```

---

## 🎯 Success Criteria

Deployment is successful when:

- ✅ All containers are running and healthy
- ✅ Frontend accessible at configured URL
- ✅ Backend API responding to requests
- ✅ Airflow DAG running without errors
- ✅ Tee times being fetched and saved to database
- ✅ Email notifications being sent
- ✅ No critical errors in logs

---

## 🔗 Additional Resources

- **Docker Documentation**: https://docs.docker.com/
- **Docker Compose**: https://docs.docker.com/compose/
- **Airflow**: https://airflow.apache.org/docs/
- **FastAPI**: https://fastapi.tiangolo.com/
- **PostgreSQL**: https://www.postgresql.org/docs/

---

**Ready to deploy?** Start with [QUICKSTART_DEPLOYMENT.md](QUICKSTART_DEPLOYMENT.md) →
