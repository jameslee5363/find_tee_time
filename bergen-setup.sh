#!/bin/bash

# Bergen Tee Notifier VPS Setup Script
# Customized for bergen-tee-notifier.com
# Run this on a fresh Ubuntu 22.04 VPS as root

set -e

# Configuration - UPDATE THESE!
DOMAIN_NAME="bergen-tee-notifier.com"
EMAIL="jameslee5363@gmail.com"  # CHANGE THIS to your email
GITHUB_REPO="https://github.com/yourusername/your-repo.git"  # CHANGE THIS to your repo

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Header
clear
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Bergen Tee Notifier Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   log_error "This script must be run as root"
   exit 1
fi

# Confirm settings
log_info "Setup Configuration:"
echo "  Domain: $DOMAIN_NAME"
echo "  Email: $EMAIL"
echo "  Repository: $GITHUB_REPO"
echo ""
read -p "Are these settings correct? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_error "Please edit this script and update the configuration variables at the top"
    exit 1
fi

# System Update
log_info "Updating system packages..."
apt update && apt upgrade -y

# Install required packages
log_info "Installing required packages..."
apt install -y \
    curl \
    git \
    nginx \
    certbot \
    python3-certbot-nginx \
    ufw \
    htop \
    ncdu \
    nano

# Install Docker
log_info "Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
else
    log_info "Docker already installed"
fi

# Install Docker Compose
log_info "Installing Docker Compose..."
apt install -y docker-compose-plugin

# Create deploy user
log_info "Creating deploy user..."
if ! id -u deploy &>/dev/null; then
    adduser --disabled-password --gecos "" deploy
    usermod -aG docker deploy
    usermod -aG sudo deploy
else
    log_info "Deploy user already exists"
fi

# Setup firewall
log_info "Configuring firewall..."
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# Clone repository
log_info "Cloning repository..."
su - deploy -c "
    if [ ! -d ~/bergen-tee-notifier ]; then
        git clone $GITHUB_REPO ~/bergen-tee-notifier
    else
        cd ~/bergen-tee-notifier && git pull origin main
    fi
"

# Create .env.production
log_info "Creating environment configuration..."
cat > /home/deploy/bergen-tee-notifier/.env.production << 'EOF'
# Bergen Tee Notifier Production Configuration
# Generated on: DATE_PLACEHOLDER

# Database Configuration
POSTGRES_USER=bergen_tee_prod
POSTGRES_PASSWORD=DB_PASSWORD_PLACEHOLDER
POSTGRES_DB=bergen_tee
POSTGRES_PORT=5433

# Airflow Configuration
AIRFLOW_UID=50000
_AIRFLOW_WWW_USER_USERNAME=admin
_AIRFLOW_WWW_USER_PASSWORD=AIRFLOW_PASSWORD_PLACEHOLDER
AIRFLOW_WEBSERVER_PORT=8081

# Backend Configuration
BACKEND_PORT=8000
JWT_SECRET_KEY=JWT_SECRET_PLACEHOLDER
PRODUCTION_FRONTEND_URL=https://bergen-tee-notifier.com

# Frontend Configuration
FRONTEND_PORT=3000
REACT_APP_API_URL=https://api.bergen-tee-notifier.com

# Email Configuration (Gmail example - update with your settings)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=UPDATE_WITH_YOUR_EMAIL@gmail.com
SMTP_PASSWORD=UPDATE_WITH_APP_PASSWORD
FROM_EMAIL=UPDATE_WITH_YOUR_EMAIL@gmail.com

# Notifier Configuration
NOTIFIER_MODE=both
MATCHER_CHECK_INTERVAL=300
EOF

# Add timestamp
sed -i "s/DATE_PLACEHOLDER/$(date '+%Y-%m-%d %H:%M:%S')/g" /home/deploy/bergen-tee-notifier/.env.production

# Generate random secrets
log_info "Generating secure secrets..."
JWT_SECRET=$(openssl rand -base64 48)
DB_PASSWORD=$(openssl rand -base64 32)
AIRFLOW_PASSWORD=$(openssl rand -base64 16)

sed -i "s/JWT_SECRET_PLACEHOLDER/$JWT_SECRET/g" /home/deploy/bergen-tee-notifier/.env.production
sed -i "s/DB_PASSWORD_PLACEHOLDER/$DB_PASSWORD/g" /home/deploy/bergen-tee-notifier/.env.production
sed -i "s/AIRFLOW_PASSWORD_PLACEHOLDER/$AIRFLOW_PASSWORD/g" /home/deploy/bergen-tee-notifier/.env.production

chown deploy:deploy /home/deploy/bergen-tee-notifier/.env.production
chmod 600 /home/deploy/bergen-tee-notifier/.env.production

# Configure Nginx
log_info "Configuring Nginx..."
cat > /etc/nginx/sites-available/bergen-tee-notifier << 'EOF'
# API Backend
server {
    listen 80;
    server_name api.bergen-tee-notifier.com;

    client_max_body_size 10M;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}

# Frontend
server {
    listen 80;
    server_name bergen-tee-notifier.com www.bergen-tee-notifier.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}

# Airflow
server {
    listen 80;
    server_name airflow.bergen-tee-notifier.com;

    location / {
        proxy_pass http://localhost:8081;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
EOF

# Enable Nginx site
ln -sf /etc/nginx/sites-available/bergen-tee-notifier /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# Create helper scripts
log_info "Creating helper scripts..."

# Deploy script
cat > /home/deploy/deploy.sh << 'EOF'
#!/bin/bash
cd ~/bergen-tee-notifier

echo "🚀 Starting deployment..."
echo "Pulling latest code..."
git pull origin main

echo "Stopping current services..."
docker compose -f docker-compose.prod.yml down

echo "Building and starting services..."
docker compose -f docker-compose.prod.yml --env-file .env.production build
docker compose -f docker-compose.prod.yml --env-file .env.production up -d

echo "Waiting for services to start..."
sleep 15

echo "Running database migrations (if any)..."
docker compose -f docker-compose.prod.yml exec -T backend alembic upgrade head 2>/dev/null || echo "No migrations to run"

echo "Service status:"
docker compose -f docker-compose.prod.yml ps

echo "✅ Deployment complete!"
echo ""
echo "Check your services:"
echo "  Frontend: https://bergen-tee-notifier.com"
echo "  API: https://api.bergen-tee-notifier.com"
echo "  Airflow: https://airflow.bergen-tee-notifier.com"
EOF

# Monitor script
cat > /home/deploy/monitor.sh << 'EOF'
#!/bin/bash

echo "=== Bergen Tee Notifier Status ==="
echo "Time: $(date)"
echo ""

cd ~/bergen-tee-notifier

echo "Docker Services:"
docker compose -f docker-compose.prod.yml ps
echo ""

echo "Health Checks:"
# Backend
if curl -f -s http://localhost:8000/ > /dev/null 2>&1; then
    echo "✅ Backend API: Running"
else
    echo "❌ Backend API: Not responding"
fi

# Frontend
if curl -f -s http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ Frontend: Running"
else
    echo "❌ Frontend: Not responding"
fi

# Database
if docker compose -f docker-compose.prod.yml exec -T postgres pg_isready > /dev/null 2>&1; then
    echo "✅ PostgreSQL: Running"
else
    echo "❌ PostgreSQL: Not responding"
fi

# Kafka
if docker compose -f docker-compose.prod.yml exec -T kafka kafka-broker-api-versions --bootstrap-server localhost:9092 > /dev/null 2>&1; then
    echo "✅ Kafka: Running"
else
    echo "❌ Kafka: Not responding"
fi

# Airflow
if curl -f -s http://localhost:8081/health > /dev/null 2>&1; then
    echo "✅ Airflow: Running"
else
    echo "❌ Airflow: Not responding"
fi

echo ""
echo "System Resources:"
echo "Disk usage:"
df -h | grep -E '^/dev/' | head -1
echo "Memory usage:"
free -h | grep Mem
echo "Docker disk usage:"
docker system df
EOF

# Backup script
cat > /home/deploy/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/deploy/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

cd ~/bergen-tee-notifier

echo "Creating backup..."
# Backup database
docker compose -f docker-compose.prod.yml exec -T postgres \
    pg_dump -U bergen_tee_prod bergen_tee > "$BACKUP_DIR/database.sql" 2>/dev/null || echo "Database backup skipped"

# Backup environment
cp .env.production "$BACKUP_DIR/.env.production"

# Create archive
tar -czf "$BACKUP_DIR.tar.gz" -C "$BACKUP_DIR" .
rm -rf "$BACKUP_DIR"

echo "Backup created: $BACKUP_DIR.tar.gz"

# Keep only last 7 backups
find /home/deploy/backups -name "*.tar.gz" -mtime +7 -delete
EOF

# Make scripts executable
chmod +x /home/deploy/*.sh
chown deploy:deploy /home/deploy/*.sh

# Create directories
su - deploy -c "mkdir -p ~/logs ~/backups"

# Initial deployment
log_info "Starting initial deployment..."
su - deploy -c "cd ~/bergen-tee-notifier && ./deploy.sh"

# Wait for DNS propagation
log_info "Waiting for DNS to propagate (this may take a few minutes)..."
sleep 30

# Setup SSL certificates
log_info "Setting up SSL certificates..."
certbot --nginx \
    -d bergen-tee-notifier.com \
    -d www.bergen-tee-notifier.com \
    -d api.bergen-tee-notifier.com \
    -d airflow.bergen-tee-notifier.com \
    --non-interactive \
    --agree-tos \
    --email $EMAIL \
    --redirect || log_warn "SSL setup failed - DNS may still be propagating. Run 'certbot --nginx' later."

# Setup cron jobs
log_info "Setting up automated tasks..."
cat > /tmp/deploy-crontab << EOF
# Daily backup at 2 AM
0 2 * * * /home/deploy/backup.sh >> /home/deploy/logs/backup.log 2>&1

# SSL renewal check twice daily
0 0,12 * * * certbot renew --quiet

# Health check every 5 minutes (optional - comment out if not needed)
*/5 * * * * /home/deploy/monitor.sh >> /home/deploy/logs/monitor.log 2>&1
EOF

su - deploy -c "crontab /tmp/deploy-crontab"
rm /tmp/deploy-crontab

# Create systemd service
log_info "Creating systemd service for auto-start..."
cat > /etc/systemd/system/bergen-tee-notifier.service << EOF
[Unit]
Description=Bergen Tee Notifier Application
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
User=deploy
WorkingDirectory=/home/deploy/bergen-tee-notifier
ExecStart=/usr/bin/docker compose -f docker-compose.prod.yml --env-file .env.production up -d
ExecStop=/usr/bin/docker compose -f docker-compose.prod.yml down
StandardOutput=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable bergen-tee-notifier.service

# Save credentials
log_info "Saving credentials..."
cat > /home/deploy/CREDENTIALS.txt << EOF
Bergen Tee Notifier - Production Credentials
Generated: $(date)
=========================================

Airflow Admin Panel:
URL: https://airflow.bergen-tee-notifier.com
Username: admin
Password: $AIRFLOW_PASSWORD

PostgreSQL Database:
Host: localhost
Port: 5433
Database: bergen_tee
Username: bergen_tee_prod
Password: $DB_PASSWORD

JWT Secret (for backend):
$JWT_SECRET

IMPORTANT: Save these credentials securely!
Update email settings in .env.production file.
EOF

chown deploy:deploy /home/deploy/CREDENTIALS.txt
chmod 600 /home/deploy/CREDENTIALS.txt

# Final summary
clear
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   🎉 Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
log_info "Bergen Tee Notifier is now deployed!"
echo ""
echo "📱 Access your services:"
echo "  Frontend: https://bergen-tee-notifier.com"
echo "  API: https://api.bergen-tee-notifier.com"
echo "  Airflow: https://airflow.bergen-tee-notifier.com"
echo ""
echo "📁 Important files:"
echo "  Credentials: /home/deploy/CREDENTIALS.txt"
echo "  Environment: /home/deploy/bergen-tee-notifier/.env.production"
echo "  Deploy script: /home/deploy/deploy.sh"
echo "  Monitor script: /home/deploy/monitor.sh"
echo ""
echo "⚠️  CRITICAL NEXT STEPS:"
echo "1. Save credentials: cat /home/deploy/CREDENTIALS.txt"
echo "2. Update email settings:"
echo "   su - deploy"
echo "   nano ~/bergen-tee-notifier/.env.production"
echo "   (Update SMTP_USER, SMTP_PASSWORD, FROM_EMAIL)"
echo "3. Restart after email update:"
echo "   ./deploy.sh"
echo ""
echo "🔧 Useful commands:"
echo "  Switch to deploy user: su - deploy"
echo "  Check status: ./monitor.sh"
echo "  View logs: docker compose -f docker-compose.prod.yml logs -f"
echo "  Deploy updates: ./deploy.sh"
echo "  Create backup: ./backup.sh"
echo ""
log_warn "⚠️  Remember to save the credentials and update email settings!"
