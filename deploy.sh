#!/bin/bash

# Tee Time Finder - Production Deployment Script
# This script helps automate the deployment process

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Tee Time Finder - Production Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker installed${NC}"
echo -e "${GREEN}✓ Docker Compose installed${NC}"
echo ""

# Check if .env.production exists
if [ ! -f .env.production ]; then
    echo -e "${YELLOW}Warning: .env.production does not exist${NC}"
    echo "Would you like to create it from template? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        cp .env.production.example .env.production
        echo -e "${GREEN}✓ Created .env.production${NC}"
        echo ""
        echo -e "${RED}IMPORTANT: Edit .env.production with your actual values before continuing!${NC}"
        echo "Press Enter when ready..."
        read -r
    else
        echo -e "${RED}Error: Cannot continue without .env.production${NC}"
        exit 1
    fi
fi

# Secure .env.production
chmod 600 .env.production
echo -e "${GREEN}✓ Secured .env.production (chmod 600)${NC}"
echo ""

# Set Airflow UID if not already set
if ! grep -q "AIRFLOW_UID" .env.production; then
    echo "AIRFLOW_UID=$(id -u)" >> .env.production
    echo -e "${GREEN}✓ Set AIRFLOW_UID${NC}"
fi

# Create required directories
echo -e "${YELLOW}Creating required directories...${NC}"
mkdir -p backend/logs backend/plugins
chmod -R 777 backend/logs backend/plugins
echo -e "${GREEN}✓ Created directories${NC}"
echo ""

# Ask deployment action
echo "Select deployment action:"
echo "1) Fresh deployment (build and start all services)"
echo "2) Update deployment (rebuild and restart)"
echo "3) Start existing services"
echo "4) Stop all services"
echo "5) View logs"
echo "6) Check service status"
echo "7) Backup database"
echo "8) Exit"
echo ""
read -p "Enter choice [1-8]: " choice

case $choice in
    1)
        echo -e "${YELLOW}Building services (this may take several minutes)...${NC}"
        docker-compose -f docker-compose.prod.yml --env-file .env.production build

        echo ""
        echo -e "${YELLOW}Starting all services...${NC}"
        docker-compose -f docker-compose.prod.yml --env-file .env.production up -d

        echo ""
        echo -e "${GREEN}✓ Services started${NC}"
        echo ""
        echo "Waiting for services to be healthy (30 seconds)..."
        sleep 30

        echo ""
        echo -e "${YELLOW}Service Status:${NC}"
        docker-compose -f docker-compose.prod.yml ps

        echo ""
        echo -e "${GREEN}Deployment complete!${NC}"
        echo ""
        echo "Next steps:"
        echo "1. Access Airflow UI: http://localhost:8081"
        echo "2. Login with credentials from .env.production"
        echo "3. Add Variables: golf_username, golf_password, kafka_bootstrap_servers"
        echo "4. Enable tee_time_checker_dag"
        echo "5. Access frontend: http://localhost:3000"
        echo ""
        echo "To view logs: ./deploy.sh (select option 5)"
        ;;

    2)
        echo -e "${YELLOW}Updating deployment...${NC}"
        docker-compose -f docker-compose.prod.yml --env-file .env.production up -d --build

        echo ""
        echo -e "${GREEN}✓ Services updated${NC}"
        docker-compose -f docker-compose.prod.yml ps
        ;;

    3)
        echo -e "${YELLOW}Starting services...${NC}"
        docker-compose -f docker-compose.prod.yml --env-file .env.production start

        echo ""
        echo -e "${GREEN}✓ Services started${NC}"
        docker-compose -f docker-compose.prod.yml ps
        ;;

    4)
        echo -e "${YELLOW}Stopping services...${NC}"
        docker-compose -f docker-compose.prod.yml stop

        echo ""
        echo -e "${GREEN}✓ Services stopped${NC}"
        ;;

    5)
        echo -e "${YELLOW}Viewing logs (Ctrl+C to exit)...${NC}"
        docker-compose -f docker-compose.prod.yml logs -f
        ;;

    6)
        echo -e "${YELLOW}Service Status:${NC}"
        docker-compose -f docker-compose.prod.yml ps

        echo ""
        echo -e "${YELLOW}Resource Usage:${NC}"
        docker stats --no-stream
        ;;

    7)
        BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql.gz"
        echo -e "${YELLOW}Creating database backup: ${BACKUP_FILE}${NC}"
        docker exec postgres-prod pg_dump -U airflow app | gzip > "$BACKUP_FILE"

        echo ""
        echo -e "${GREEN}✓ Backup created: ${BACKUP_FILE}${NC}"
        echo "Size: $(ls -lh "$BACKUP_FILE" | awk '{print $5}')"
        ;;

    8)
        echo "Exiting..."
        exit 0
        ;;

    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
