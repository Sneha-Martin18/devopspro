#!/bin/bash

# Setup and Data Migration Script for Django Student Management System
# This script starts microservices, creates databases, and migrates data from SQLite

set -e

echo "============================================================"
echo "🚀 Django Student Management System - Setup & Migration"
echo "   SQLite → PostgreSQL Microservices"
echo "============================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if Docker and Docker Compose are installed
check_dependencies() {
    print_info "Checking dependencies..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3 first."
        exit 1
    fi
    
    print_status "All dependencies are available"
}

# Install Python dependencies for migration
install_python_deps() {
    print_info "Installing Python dependencies for migration..."
    
    if [ -f "migration_requirements.txt" ]; then
        pip3 install -r migration_requirements.txt
        print_status "Python dependencies installed"
    else
        print_warning "migration_requirements.txt not found, installing manually..."
        pip3 install psycopg2-binary
        print_status "psycopg2-binary installed"
    fi
}

# Start microservices
start_microservices() {
    print_info "Starting microservices..."
    
    cd microservices
    
    # Stop any existing containers
    docker compose down --remove-orphans
    
    # Build and start services
    docker compose up --build -d
    
    print_status "Microservices started"
    
    # Wait for services to be healthy
    print_info "Waiting for services to be healthy..."
    sleep 30
    
    # Check service health
    docker compose ps
}

# Create PostgreSQL databases
create_databases() {
    print_info "Creating PostgreSQL databases..."
    
    # List of databases to create
    databases=(
        "user_service_db"
        "academic_service_db"
        "attendance_service_db"
        "notification_service_db"
        "leave_management_db"
        "feedback_service_db"
        "assessment_service_db"
        "financial_service_db"
    )
    
    for db in "${databases[@]}"; do
        print_info "Creating database: $db"
        docker compose exec -T postgres psql -U postgres -c "CREATE DATABASE $db;" 2>/dev/null || print_warning "Database $db may already exist"
    done
    
    print_status "All databases created/verified"
}

# Run Django migrations for all services
run_migrations() {
    print_info "Running Django migrations for all services..."
    
    # User Management Service
    print_info "Migrating User Management Service..."
    docker compose exec -T user-management python manage.py makemigrations
    docker compose exec -T user-management python manage.py migrate
    
    # Academic Service
    print_info "Migrating Academic Service..."
    docker compose exec -T academic python manage.py makemigrations
    docker compose exec -T academic python manage.py migrate
    
    # Attendance Service
    print_info "Migrating Attendance Service..."
    docker compose exec -T attendance python manage.py makemigrations
    docker compose exec -T attendance python manage.py migrate
    
    # Notification Service
    print_info "Migrating Notification Service..."
    docker compose exec -T notification python manage.py makemigrations
    docker compose exec -T notification python manage.py migrate
    
    # Leave Management Service
    print_info "Migrating Leave Management Service..."
    docker compose exec -T leave-management python manage.py makemigrations
    docker compose exec -T leave-management python manage.py migrate
    
    # Feedback Service
    print_info "Migrating Feedback Service..."
    docker compose exec -T feedback python manage.py makemigrations
    docker compose exec -T feedback python manage.py migrate
    
    # Assessment Service
    print_info "Migrating Assessment Service..."
    docker compose exec -T assessment python manage.py makemigrations
    docker compose exec -T assessment python manage.py migrate
    
    # Financial Service
    print_info "Migrating Financial Service..."
    docker compose exec -T financial python manage.py makemigrations
    docker compose exec -T financial python manage.py migrate
    
    print_status "All Django migrations completed"
}

# Run data migration from SQLite
migrate_data() {
    print_info "Starting data migration from SQLite to PostgreSQL..."
    
    cd ..
    
    # Check if SQLite database exists
    if [ ! -f "db.sqlite3" ]; then
        print_error "SQLite database (db.sqlite3) not found!"
        print_info "Please ensure the original db.sqlite3 file exists in the project root."
        return 1
    fi
    
    # Run the migration script
    python3 migrate_data.py
    
    if [ $? -eq 0 ]; then
        print_status "Data migration completed successfully!"
    else
        print_error "Data migration failed!"
        return 1
    fi
}

# Verify services are running
verify_services() {
    print_info "Verifying all services are running..."
    
    cd microservices
    
    # Check service health endpoints
    services=(
        "http://localhost:8080/health"
        "http://localhost:8000/api/v1/users/health/"
        "http://localhost:8001/api/v1/academics/health/"
        "http://localhost:8002/api/v1/attendance/health/"
        "http://localhost:8003/health/"
        "http://localhost:8004/health/"
        "http://localhost:8005/health/"
        "http://localhost:8006/health/"
        "http://localhost:8007/health/"
        "http://localhost:9000/health/"
    )
    
    for service in "${services[@]}"; do
        if curl -f -s "$service" > /dev/null; then
            print_status "Service healthy: $service"
        else
            print_warning "Service may not be ready: $service"
        fi
    done
    
    print_info "Service verification completed"
}

# Main execution
main() {
    print_info "Starting setup and migration process..."
    
    # Step 1: Check dependencies
    check_dependencies
    
    # Step 2: Install Python dependencies
    install_python_deps
    
    # Step 3: Start microservices
    start_microservices
    
    # Step 4: Create databases
    create_databases
    
    # Step 5: Run Django migrations
    run_migrations
    
    # Step 6: Migrate data from SQLite
    migrate_data
    
    # Step 7: Verify services
    verify_services
    
    print_status "Setup and migration completed successfully!"
    print_info "You can now access the application at:"
    print_info "  - Frontend: http://localhost:9000"
    print_info "  - API Gateway: http://localhost:8080"
    print_info "  - API Documentation: http://localhost:8080/docs"
    
    echo ""
    print_info "Admin credentials (if migrated):"
    print_info "  - Email: admin@gmail.com"
    print_info "  - Password: admin"
}

# Handle script interruption
trap 'print_error "Script interrupted by user"; exit 1' INT

# Run main function
main "$@"
