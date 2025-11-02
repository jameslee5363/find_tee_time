#!/bin/bash

# AWS EC2 Deployment Script for Tee Time Finder
# Run this script ON YOUR AWS EC2 SERVER after uploading code

set -e  # Exit on error

echo "========================================"
echo "Tee Time Finder - AWS EC2 Deployment"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if running on AWS EC2
if [ ! -f /sys/hypervisor/uuid ] && ! grep -q ec2 /sys/hypervisor/uuid 2>/dev/null && ! grep -q "Amazon EC2" /sys/devices/virtual/dmi/id/product_name 2>/dev/null; then
    echo -e "${YELLOW}Warning: This doesn't appear to be an AWS EC2 instance.${NC}"
    echo -e "${YELLOW}This script is designed for EC2. Continue anyway? (y/N)${NC}"
    read -p "> " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled."
        exit 0
    fi
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}ERROR: Docker is not installed!${NC}"
    echo ""
    echo "Please install Docker first:"
    echo "  curl -fsSL https://get.docker.com -o get-docker.sh"
    echo "  sudo sh get-docker.sh"
    echo "  sudo usermod -aG docker \$USER"
    echo ""
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}ERROR: docker-compose is not installed!${NC}"
    echo ""
    echo "Please install docker-compose first:"
    echo "  sudo apt install docker-compose -y"
    echo ""
    exit 1
fi

# Check if .env.production exists
if [ ! -f .env.production ]; then
    echo -e "${RED}ERROR: .env.production file not found!${NC}"
    echo ""
    echo "Please create .env.production from the template:"
    echo "  cp .env.production.example .env.production"
    echo ""
    echo "Then edit .env.production and update:"
    echo "  - PRODUCTION_FRONTEND_URL to your domain"
    echo "  - REACT_APP_API_URL to your API domain"
    echo "  - Change all passwords to strong values"
    echo ""
    exit 1
fi

# Check if production URLs are configured
if grep -q "localhost" .env.production; then
    echo -e "${YELLOW}WARNING: Found 'localhost' in .env.production${NC}"
    echo "Make sure you've updated the URLs to your actual domain:"
    echo "  - PRODUCTION_FRONTEND_URL=https://bergen_tee_notifier.com"
    echo "  - REACT_APP_API_URL=https://api.bergen_tee_notifier.com"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled. Please update .env.production first."
        exit 0
    fi
fi

echo -e "${GREEN}✓${NC} Docker is installed"
echo -e "${GREEN}✓${NC} docker-compose is installed"
echo -e "${GREEN}✓${NC} Environment file found"
echo ""

echo "This will deploy your application with the following steps:"
echo "  1. Stop any existing containers"
echo "  2. Pull latest images"
echo "  3. Build production images"
echo "  4. Start all services"
echo "  5. Show deployment status"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

echo ""
echo "Step 1/5: Stopping existing containers..."
docker-compose -f docker-compose.prod.yml down 2>/dev/null || true

echo ""
echo "Step 2/5: Pulling latest base images..."
docker-compose -f docker-compose.prod.yml pull 2>/dev/null || echo "Some images need to be built locally"

echo ""
echo "Step 3/5: Building production images (this may take 5-10 minutes)..."
docker-compose -f docker-compose.prod.yml --env-file .env.production build

echo ""
echo "Step 4/5: Starting all services..."
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d

echo ""
echo "Step 5/5: Waiting for services to initialize (30 seconds)..."
sleep 30

echo ""
echo "========================================"
echo "Deployment Status"
echo "========================================"
docker-compose -f docker-compose.prod.yml ps

echo ""
echo "========================================"
echo "Health Checks"
echo "========================================"

# Check backend
if curl -s http://localhost:8000/ | grep -q "Hello from backend"; then
    echo -e "${GREEN}✓${NC} Backend API is responding"
else
    echo -e "${RED}✗${NC} Backend API is not responding"
fi

# Check frontend
if curl -s http://localhost:3000/ | grep -q "html"; then
    echo -e "${GREEN}✓${NC} Frontend is serving content"
else
    echo -e "${RED}✗${NC} Frontend is not responding"
fi

# Check Airflow
if curl -s http://localhost:8081/health 2>/dev/null | grep -q "healthy"; then
    echo -e "${GREEN}✓${NC} Airflow is healthy"
else
    echo -e "${YELLOW}⚠${NC} Airflow may still be starting up"
fi

# Check database
if docker exec postgres-prod pg_isready -U airflow >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Database is ready"
else
    echo -e "${RED}✗${NC} Database is not ready"
fi

echo ""
echo "========================================"
echo "Next Steps"
echo "========================================"
echo ""
echo "1. Check that your domain DNS is configured:"
echo "   - bergen_tee_notifier.com → Your Elastic IP"
echo "   - api.bergen_tee_notifier.com → Your Elastic IP"
echo ""
echo "2. Set up Nginx reverse proxy (if not done yet):"
echo "   See AWS_DEPLOYMENT_GUIDE.md Step 7"
echo ""
echo "3. Install SSL certificates:"
echo "   sudo certbot --nginx -d bergen_tee_notifier.com -d api.bergen_tee_notifier.com"
echo ""
echo "4. Enable the Airflow DAG:"
echo "   Go to https://airflow.bergen_tee_notifier.com"
echo "   Toggle the 'bergen_county_golf_tee_times' DAG ON"
echo ""
echo "5. Test your application:"
echo "   https://bergen_tee_notifier.com"
echo ""
echo "========================================"
echo ""
echo -e "${GREEN}✓ Deployment complete!${NC}"
echo ""
echo "View logs:"
echo "  docker-compose -f docker-compose.prod.yml logs -f"
echo ""
echo "Stop services:"
echo "  docker-compose -f docker-compose.prod.yml down"
echo ""
