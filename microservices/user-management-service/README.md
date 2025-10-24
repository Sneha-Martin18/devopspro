# User Management Service

A standalone Django REST API service for managing users, authentication, and user profiles in a microservices architecture.

## Features

- **User Authentication**: JWT-based authentication with login/logout
- **User Management**: Create, read, update, delete users (Students, Staff, Admin HOD)
- **Profile Management**: Manage user profiles with role-specific data
- **Session Tracking**: Track user sessions for security and analytics
- **Inter-service Communication**: REST API endpoints for other services
- **Asynchronous Tasks**: Email notifications and background processing
- **API Documentation**: Auto-generated OpenAPI/Swagger documentation

## Architecture

This service is part of a microservices architecture extracted from a Django monolith. It handles:

- User authentication and authorization
- User profile management
- Session management
- Inter-service user data provision

## Tech Stack

- **Framework**: Django 4.2.7 + Django REST Framework
- **Database**: PostgreSQL
- **Authentication**: JWT (Simple JWT)
- **Task Queue**: Celery + Redis
- **Documentation**: drf-spectacular
- **Containerization**: Docker + Docker Compose

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- PostgreSQL (if running locally)
- Redis (if running locally)

### Using Docker Compose (Recommended)

1. **Clone and navigate to the service directory**:
   ```bash
   cd microservices/user-management-service
   ```

2. **Create environment file**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Build and start services**:
   ```bash
   docker compose up --build
   ```

4. **Run migrations**:
   ```bash
   docker compose exec web python manage.py migrate
   ```

5. **Create superuser**:
   ```bash
   docker compose exec web python manage.py createsuperuser
   ```

6. **Access the service**:
   - API: http://localhost:8000/api/v1/users/
   - Admin: http://localhost:8000/admin/
   - API Docs: http://localhost:8000/api/docs/

### Local Development Setup

1. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Configure your database and other settings
   ```

4. **Run migrations**:
   ```bash
   python manage.py migrate
   ```

5. **Create superuser**:
   ```bash
   python manage.py createsuperuser
   ```

6. **Start development server**:
   ```bash
   python manage.py runserver 8000
   ```

7. **Start Celery worker** (in another terminal):
   ```bash
   celery -A user_service worker --loglevel=info
   ```

## API Endpoints

### Authentication
- `POST /api/v1/users/register/` - Register new user
- `POST /api/v1/users/login/` - User login
- `POST /api/v1/users/logout/` - User logout
- `POST /api/v1/users/token/refresh/` - Refresh JWT token

### User Profile
- `GET /api/v1/users/profile/` - Get current user profile
- `PATCH /api/v1/users/profile/` - Update current user profile
- `POST /api/v1/users/change-password/` - Change password
- `GET /api/v1/users/sessions/` - Get user session history

### Students
- `GET /api/v1/users/students/` - List students
- `POST /api/v1/users/students/` - Create student
- `GET /api/v1/users/students/{id}/` - Get student details
- `PATCH /api/v1/users/students/{id}/` - Update student
- `DELETE /api/v1/users/students/{id}/` - Delete student

### Staff
- `GET /api/v1/users/staff/` - List staff
- `POST /api/v1/users/staff/` - Create staff
- `GET /api/v1/users/staff/{id}/` - Get staff details
- `PATCH /api/v1/users/staff/{id}/` - Update staff
- `DELETE /api/v1/users/staff/{id}/` - Delete staff

### Admin HODs
- `GET /api/v1/users/admins/` - List admin HODs

### Inter-service Communication
- `GET /api/v1/users/user/{id}/` - Get user by ID
- `GET /api/v1/users/validate-token/` - Validate JWT token
- `GET /api/v1/users/health/` - Health check

## Environment Variables

Create a `.env` file based on `.env.example`:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Database Configuration
DB_NAME=user_service_db
DB_USER=postgres
DB_PASSWORD=password
DB_HOST=localhost
DB_PORT=5432

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

## Database Models

### CustomUser
Extended Django user model with user type classification (HOD, Staff, Student).

### AdminHOD
Profile for Head of Department users.

### Staff
Profile for staff members with employment details.

### Student
Profile for students with academic information.

### UserSession
Tracks user login sessions for security and analytics.

## Inter-service Communication

This service provides endpoints for other microservices to:

1. **Validate user tokens**: Other services can validate JWT tokens
2. **Get user information**: Retrieve user details by ID
3. **Receive notifications**: About user-related events

### Service Clients

The service includes client utilities for communicating with other services:

- `AcademicServiceClient`: For course and enrollment validation
- `NotificationServiceClient`: For sending notifications
- `AttendanceServiceClient`: For attendance-related operations

## Deployment

### Docker Deployment

1. **Build the image**:
   ```bash
   docker build -t user-management-service .
   ```

2. **Run with Docker Compose**:
   ```bash
   docker compose -f docker compose.prod.yml up -d
   ```

### Production Considerations

1. **Environment Variables**: Use secure values for production
2. **Database**: Use managed PostgreSQL service
3. **Redis**: Use managed Redis service
4. **Static Files**: Serve static files with nginx
5. **SSL/TLS**: Enable HTTPS
6. **Monitoring**: Add health checks and monitoring
7. **Logging**: Configure proper logging levels

## Testing

Run tests with:

```bash
python manage.py test
```

For coverage:

```bash
coverage run --source='.' manage.py test
coverage report
```

## Monitoring and Health Checks

- **Health Check**: `GET /api/v1/users/health/`
- **Service Status**: Monitor via Docker health checks
- **Logs**: Check application logs for errors
- **Database**: Monitor PostgreSQL performance
- **Redis**: Monitor Redis memory usage

## Migration from Monolith

This service was extracted from a Django monolith. Key changes:

1. **Database**: Moved from SQLite to PostgreSQL
2. **Authentication**: Switched to JWT from session-based
3. **Communication**: Added REST API endpoints for inter-service communication
4. **Dependencies**: Removed dependencies on other monolith components
5. **Configuration**: Environment-based configuration

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License.
