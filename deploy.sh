#!/bin/bash

# Production Deployment Script for Tee Time Finder
# This script helps deploy the application to production

set -e  # Exit on error

echo "========================================"
echo "Tee Time Finder - Production Deployment"
echo "========================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if .env.production exists
if [ ! -f .env.production ]; then
    echo -e "${RED}ERROR: .env.production file not found!${NC}"
    echo ""
    echo "Please create .env.production from the template:"
    echo "  cp .env.production.example .env.production"
    echo ""
    echo "Then edit .env.production and fill in your production values."
    exit 1
fi

# Check Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}ERROR: Docker is not running!${NC}"
    echo "Please start Docker and try again."
    exit 1
fi

echo -e "${GREEN}✓${NC} Docker is running"
echo -e "${GREEN}✓${NC} Environment file found"
echo ""

# Ask for confirmation
echo -e "${YELLOW}This will:${NC}"
echo "  1. Stop any existing production containers"
echo "  2. Build new production images"
echo "  3. Start all services"
echo ""
read -p "Continue with deployment? (y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

echo ""
echo "Step 1/4: Stopping existing containers..."
docker-compose -f docker-compose.prod.yml down 2>/dev/null || true

echo ""
echo "Step 2/4: Building production images..."
docker-compose -f docker-compose.prod.yml --env-file .env.production build --no-cache

echo ""
echo "Step 3/4: Starting services..."
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d

echo ""
echo "Step 4/4: Waiting for services to be healthy..."
sleep 10

echo ""
echo "========================================"
echo "Deployment Status"
echo "========================================"
docker-compose -f docker-compose.prod.yml ps

echo ""
echo "========================================"
echo "Service URLs"
echo "========================================"
echo -e "${GREEN}Frontend:${NC}       http://localhost:3000"
echo -e "${GREEN}Backend API:${NC}    http://localhost:8000"
echo -e "${GREEN}Airflow UI:${NC}     http://localhost:8081"
echo -e "${GREEN}  Username:${NC}     airflow"
echo -e "${GREEN}  Password:${NC}     (check .env.production)"
echo ""
echo "========================================"
echo ""
echo -e "${GREEN}✓ Deployment complete!${NC}"
echo ""
echo "To view logs:"
echo "  docker-compose -f docker-compose.prod.yml logs -f"
echo ""
echo "To stop services:"
echo "  docker-compose -f docker-compose.prod.yml down"
echo ""
