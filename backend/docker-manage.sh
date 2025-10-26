#!/bin/bash

# Docker Compose Management Script
# Manages Kafka (in kafka/ folder) and App services (in root)

set -e

KAFKA_DIR="kafka"
ROOT_DIR="."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${YELLOW}➜${NC} $1"
}

# Check if kafka directory exists
check_kafka_dir() {
    if [ ! -d "$KAFKA_DIR" ]; then
        print_error "Kafka directory not found at $KAFKA_DIR"
        exit 1
    fi
}

# Start all services
start_all() {
    print_info "Starting all services..."
    
    # Start Kafka first
    print_info "Starting Kafka services..."
    check_kafka_dir
    docker-compose -f "$KAFKA_DIR/docker-compose.kafka.yml" up -d
    
    # Wait for Kafka to be healthy
    print_info "Waiting for Kafka to be ready..."
    sleep 10
    
    # Start app services
    print_info "Starting application services..."
    docker-compose -f docker-compose.app.yml up -d
    
    print_success "All services started successfully!"
}

# Stop all services
stop_all() {
    print_info "Stopping all services..."
    
    # Stop app services first
    print_info "Stopping application services..."
    docker-compose -f docker-compose.app.yml down
    
    # Stop Kafka
    print_info "Stopping Kafka services..."
    check_kafka_dir
    docker-compose -f "$KAFKA_DIR/docker-compose.kafka.yml" down
    
    print_success "All services stopped successfully!"
}

# Restart all services
restart_all() {
    print_info "Restarting all services..."
    stop_all
    sleep 3
    start_all
}

# Show logs
show_logs() {
    case $1 in
        kafka)
            check_kafka_dir
            docker-compose -f "$KAFKA_DIR/docker-compose.kafka.yml" logs -f
            ;;
        app)
            docker-compose -f docker-compose.app.yml logs -f
            ;;
        *)
            print_error "Please specify 'kafka' or 'app'"
            exit 1
            ;;
    esac
}

# Show status
show_status() {
    print_info "Service Status:"
    echo "-------------------"
    echo "Kafka Services:"
    check_kafka_dir
    docker-compose -f "$KAFKA_DIR/docker-compose.kafka.yml" ps
    echo ""
    echo "Application Services:"
    docker-compose -f docker-compose.app.yml ps
}

# Clean up volumes
cleanup() {
    print_info "Cleaning up volumes and networks..."
    
    # Stop all services first
    stop_all
    
    # Remove volumes
    print_info "Removing volumes..."
    docker-compose -f docker-compose.app.yml down -v
    check_kafka_dir
    docker-compose -f "$KAFKA_DIR/docker-compose.kafka.yml" down -v
    
    # Remove network
    print_info "Removing shared network..."
    docker network rm app-network 2>/dev/null || true
    
    print_success "Cleanup completed!"
}

# Main script
case $1 in
    start)
        start_all
        ;;
    stop)
        stop_all
        ;;
    restart)
        restart_all
        ;;
    logs)
        show_logs $2
        ;;
    status)
        show_status
        ;;
    cleanup)
        cleanup
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|cleanup|logs [kafka|app]}"
        echo ""
        echo "Commands:"
        echo "  start    - Start all services (Kafka first, then app services)"
        echo "  stop     - Stop all services"
        echo "  restart  - Restart all services"
        echo "  status   - Show status of all services"
        echo "  cleanup  - Stop services and remove volumes/networks"
        echo "  logs     - Show logs (specify 'kafka' or 'app')"
        echo ""
        echo "Examples:"
        echo "  $0 start"
        echo "  $0 logs kafka"
        echo "  $0 logs app"
        exit 1
        ;;
esac