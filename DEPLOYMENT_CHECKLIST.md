# Production Deployment Checklist

Use this checklist when deploying the Tee Time Finder application to production.

---

## Pre-Deployment

### Server Setup
- [ ] Server meets minimum requirements (4GB RAM, 20GB disk)
- [ ] Docker installed (version 20.10+)
- [ ] Docker Compose installed (version 2.0+)
- [ ] Domain name configured (if applicable)
- [ ] SSL certificate obtained (Let's Encrypt recommended)
- [ ] Firewall configured (ports 22, 80, 443)

### Repository
- [ ] Code cloned to server
- [ ] Latest changes pulled from main branch

---

## Environment Configuration

### Create Production Environment File
- [ ] Copy `.env.production.example` to `.env.production`
- [ ] Set file permissions: `chmod 600 .env.production`

### Critical Security Settings
- [ ] Generate strong `JWT_SECRET_KEY` using:
  ```bash
  python3 -c "import secrets; print(secrets.token_urlsafe(64))"
  ```
- [ ] Set strong `POSTGRES_PASSWORD`
- [ ] Set strong `_AIRFLOW_WWW_USER_PASSWORD`

### URL Configuration
- [ ] Set `PRODUCTION_FRONTEND_URL` (e.g., `https://yourdomain.com`)
- [ ] Set `REACT_APP_API_URL` (e.g., `https://api.yourdomain.com`)

### Email Configuration
- [ ] Set `SMTP_USER` (your email address)
- [ ] Generate Gmail App Password at https://myaccount.google.com/apppasswords
- [ ] Set `SMTP_PASSWORD` (use App Password, NOT regular password)
- [ ] Set `FROM_EMAIL`

### Golf Course Credentials
- [ ] Set `GOLF_USERNAME`
- [ ] Set `GOLF_PASSWORD`

### Optional Settings
- [ ] Review and adjust `MATCHER_CHECK_INTERVAL` (default: 300 seconds)
- [ ] Review and adjust `NOTIFIER_MODE` (default: both)

---

## Deployment

### Build and Start
- [ ] Set Airflow UID:
  ```bash
  echo "AIRFLOW_UID=$(id -u)" >> .env.production
  ```
- [ ] Create directories:
  ```bash
  mkdir -p backend/logs backend/plugins
  chmod -R 777 backend/logs backend/plugins
  ```
- [ ] Build services:
  ```bash
  docker-compose -f docker-compose.prod.yml --env-file .env.production build
  ```
- [ ] Start services:
  ```bash
  docker-compose -f docker-compose.prod.yml --env-file .env.production up -d
  ```

### Verify Services
- [ ] All containers running:
  ```bash
  docker-compose -f docker-compose.prod.yml ps
  ```
- [ ] Check logs for errors:
  ```bash
  docker-compose -f docker-compose.prod.yml logs
  ```

---

## Post-Deployment Configuration

### Airflow Setup
- [ ] Access Airflow UI at `http://your-server:8081`
- [ ] Login with credentials from `.env.production`
- [ ] Add Variables (Admin → Variables):
  - [ ] `golf_username`
  - [ ] `golf_password`
  - [ ] `kafka_bootstrap_servers` = `kafka:29092`
- [ ] Enable `tee_time_checker_dag`
- [ ] Trigger DAG manually to test

### Verify Each Service
- [ ] Backend API responds:
  ```bash
  curl http://localhost:8000/
  ```
- [ ] Frontend accessible at `http://localhost:3000`
- [ ] Airflow UI accessible at `http://localhost:8081`
- [ ] Database accessible:
  ```bash
  docker exec postgres-prod psql -U airflow -d app -c "\dt"
  ```

### Test Notification System
- [ ] Check notifier logs:
  ```bash
  docker logs tee-time-notifier-prod --tail 50
  ```
- [ ] Verify it found tee times (should show "Found X available tee times")
- [ ] Create a test search in the app
- [ ] Verify email notification received

---

## Security Hardening

### Reverse Proxy (Production)
- [ ] Nginx/Traefik configured as reverse proxy
- [ ] SSL/TLS certificates installed
- [ ] HTTP redirects to HTTPS
- [ ] Security headers configured

### Firewall
- [ ] Close unnecessary ports
- [ ] Only expose 80 (HTTP) and 443 (HTTPS) publicly
- [ ] Internal services (PostgreSQL, Kafka, Airflow) not exposed to internet

### Secrets Management
- [ ] `.env.production` file secured (chmod 600)
- [ ] No secrets committed to Git
- [ ] Secrets rotated if previously exposed

---

## Monitoring Setup

### Log Monitoring
- [ ] Set up log rotation for Docker containers
- [ ] Configure centralized logging (optional: ELK, Loki)

### Health Checks
- [ ] Backend health endpoint monitored
- [ ] Frontend availability monitored
- [ ] Airflow scheduler running check
- [ ] Database connection monitored

### Alerts (Optional)
- [ ] Email alerts for service failures
- [ ] Disk space alerts
- [ ] Memory usage alerts

---

## Backup Strategy

### Initial Backup
- [ ] Create initial database backup:
  ```bash
  docker exec postgres-prod pg_dump -U airflow app | gzip > backup_initial.sql.gz
  ```

### Automated Backups
- [ ] Set up cron job for daily database backups
- [ ] Set up volume backups (postgres-data, kafka-data)
- [ ] Configure backup retention policy
- [ ] Test restore procedure

---

## Documentation

### Team Documentation
- [ ] Document server access credentials (securely)
- [ ] Document deployment process
- [ ] Document rollback procedure
- [ ] Document monitoring dashboards

### User Documentation
- [ ] Update user guide with production URLs
- [ ] Create FAQ for common issues
- [ ] Document support contact information

---

## Final Checks

### Functionality Tests
- [ ] User registration works
- [ ] User login works
- [ ] Create tee time search
- [ ] Verify search is saved to database
- [ ] Verify Airflow DAG runs successfully
- [ ] Verify notification email received
- [ ] Test all major user workflows

### Performance Tests
- [ ] Application responsive under load
- [ ] Database queries optimized
- [ ] No memory leaks observed
- [ ] Disk space sufficient

### Recovery Tests
- [ ] Test container restart:
  ```bash
  docker-compose -f docker-compose.prod.yml restart
  ```
- [ ] Verify data persists after restart
- [ ] Test backup restore procedure
- [ ] Document recovery time objective (RTO)

---

## Go-Live

- [ ] Announce maintenance window (if replacing existing system)
- [ ] Switch DNS to production server (if applicable)
- [ ] Monitor logs for first 24 hours
- [ ] Verify all scheduled jobs running
- [ ] Confirm user access and functionality

---

## Post-Go-Live (First 24 Hours)

- [ ] Monitor error rates
- [ ] Monitor system resources (CPU, RAM, disk)
- [ ] Monitor email delivery rates
- [ ] Check for any failed Airflow DAG runs
- [ ] Verify database growing as expected
- [ ] Respond to user feedback

---

## Post-Go-Live (First Week)

- [ ] Review logs for patterns/issues
- [ ] Optimize performance if needed
- [ ] Update documentation based on learnings
- [ ] Schedule first backup verification
- [ ] Plan first maintenance window

---

## Maintenance Schedule

### Daily
- [ ] Review application logs
- [ ] Monitor disk space
- [ ] Check for failed DAG runs

### Weekly
- [ ] Review system performance
- [ ] Check backup integrity
- [ ] Update dependencies (security patches)
- [ ] Review error logs

### Monthly
- [ ] Full system health check
- [ ] Review and rotate logs
- [ ] Test disaster recovery procedure
- [ ] Update documentation

---

## Emergency Contacts

Document the following:
- [ ] Server provider support
- [ ] Domain registrar support
- [ ] Email provider support
- [ ] Database administrator
- [ ] Application developer
- [ ] DevOps engineer

---

## Rollback Plan

In case of critical issues:

1. [ ] Stop production services:
   ```bash
   docker-compose -f docker-compose.prod.yml down
   ```
2. [ ] Restore from backup if needed
3. [ ] Switch DNS back to old system (if applicable)
4. [ ] Notify users of service restoration
5. [ ] Investigate and fix issues in staging
6. [ ] Schedule new deployment

---

## Success Criteria

Deployment is considered successful when:
- [ ] All services running without errors for 24 hours
- [ ] Users can register, login, and create searches
- [ ] Tee times are being fetched and saved to database
- [ ] Email notifications are being sent successfully
- [ ] No critical bugs reported
- [ ] System performance is acceptable
- [ ] Backups are working correctly

---

**Deployment Date:** _______________

**Deployed By:** _______________

**Sign-off:** _______________
