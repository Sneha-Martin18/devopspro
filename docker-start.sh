#!/bin/bash

# Build and start the containers
docker-compose build
docker-compose up -d

# Wait for database to be ready
echo "Waiting for database to be ready..."
sleep 10

# Create database migrations
docker-compose exec -T web python manage.py makemigrations
docker-compose exec -T web python manage.py migrate

# Collect static files
docker-compose exec -T web python manage.py collectstatic --noinput

echo "Application is now running at http://localhost:8000"
echo "To view logs, run: docker-compose logs -f"
echo "To stop the application, run: docker-compose down"
