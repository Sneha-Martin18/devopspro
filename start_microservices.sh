#!/bin/bash

echo "🚀 Starting Django Student Management System Microservices..."
echo "============================================================"

# Navigate to microservices directory
cd microservices

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker compose down

# Build and start all services
echo "🔨 Building and starting all services..."
docker compose up --build -d

# Wait for services to initialize
echo "⏳ Waiting for services to initialize..."
sleep 15

# Check service status
echo "📊 Service Status:"
docker compose ps

echo ""
echo "✅ Services Started! Access Points:"
echo "   🌐 Frontend Application: http://localhost:9000"
echo "   🚪 API Gateway: http://localhost:8080"
echo "   👥 User Management: http://localhost:8000"
echo "   📚 Academic Service: http://localhost:8001"
echo "   📋 Attendance Service: http://localhost:8002"
echo "   📧 Notification Service: http://localhost:8003"
echo "   🏖️  Leave Management: http://localhost:8004"
echo "   💬 Feedback Service: http://localhost:8005"
echo "   📝 Assessment Service: http://localhost:8006"
echo "   💰 Financial Service: http://localhost:8007"
echo ""
echo "📋 Useful Commands:"
echo "   View logs: docker compose logs -f [service-name]"
echo "   Stop all: docker compose down"
echo "   Restart: docker compose restart [service-name]"
