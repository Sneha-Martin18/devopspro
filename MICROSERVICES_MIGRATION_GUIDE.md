# Django Monolith to Microservices Migration Guide

This guide documents the complete migration from a Django monolith to a microservices architecture for the Student Management System.

## 🏗️ Architecture Overview

### Original Monolith Structure
- Single Django application with all functionality
- SQLite database
- Session-based authentication
- Tightly coupled components

### Target Microservices Architecture
```
┌─────────────────┐
│   API Gateway   │ ← Single entry point (Port 8080)
│   (Flask)       │
└─────────────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼──┐ ┌──────┐ ┌──────┐
│ User  │ │Acad │ │Atten │ │ ...  │
│ Mgmt  │ │emic │ │dance │ │      │
│:8000  │ │:8001│ │:8002 │ │      │
└───────┘ └─────┘ └──────┘ └──────┘
    │         │       │       │
    └─────────┼───────┼───────┘
              │       │
        ┌─────▼───────▼─────┐
        │   PostgreSQL      │
        │   + Redis         │
        └───────────────────┘
```

## 📋 Service Boundaries

### 1. User Management Service (✅ COMPLETED)
**Port**: 8000  
**Responsibilities**:
- User authentication (JWT)
- User profiles (Students, Staff, Admin HOD)
- Session management
- Inter-service user validation

**Models Extracted**:
- `CustomUser` → Enhanced with JWT support
- `AdminHOD` → Admin profiles
- `Staff` → Staff profiles with employment details
- `Student` → Student profiles with academic references
- `UserSession` → Session tracking for security

### 2. Academic Service (📋 TO BE IMPLEMENTED)
**Port**: 8001  
**Responsibilities**:
- Course management
- Subject management
- Session year management
- Enrollment management

**Models to Extract**:
- `Courses`
- `Subjects`
- `SessionYearModel`

### 3. Attendance Service (📋 TO BE IMPLEMENTED)
**Port**: 8002  
**Responsibilities**:
- Attendance tracking
- Attendance reports
- Attendance analytics

**Models to Extract**:
- `Attendance`
- `AttendanceReport`

### 4. Assessment Service (📋 TO BE IMPLEMENTED)
**Port**: 8003  
**Responsibilities**:
- Assignment management
- Submission handling
- Result management
- Grading system

**Models to Extract**:
- `Assignment`
- `AssignmentSubmission`
- `StudentResult`

### 5. Leave Management Service (📋 TO BE IMPLEMENTED)
**Port**: 8004  
**Responsibilities**:
- Leave requests
- Leave approvals
- Leave history

**Models to Extract**:
- `LeaveReportStudent`
- `LeaveReportStaff`

### 6. Notification Service (📋 TO BE IMPLEMENTED)
**Port**: 8005  
**Responsibilities**:
- System notifications
- Email notifications
- Push notifications

**Models to Extract**:
- `NotificationStudent`
- `NotificationStaffs`

### 7. Feedback Service (📋 TO BE IMPLEMENTED)
**Port**: 8006  
**Responsibilities**:
- Student feedback
- Staff feedback
- Feedback analytics

**Models to Extract**:
- `FeedBackStudent`
- `FeedBackStaffs`

### 8. Financial Service (📋 TO BE IMPLEMENTED)
**Port**: 8007  
**Responsibilities**:
- Fine management
- Payment processing
- Financial reports

**Models to Extract**:
- `Fine`
- `FinePayment`

## 🚀 Getting Started

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- PostgreSQL 15+
- Redis 7+

### Quick Start
1. **Navigate to microservices directory**:
   ```bash
   cd microservices/
   ```

2. **Start all services**:
   ```bash
   docker compose up --build
   ```

3. **Initialize User Management Service**:
   ```bash
   docker compose exec user-management python manage.py migrate
   docker compose exec user-management python manage.py createsuperuser
   ```

4. **Access services**:
   - API Gateway: http://localhost:8080
   - User Management: http://localhost:8000
   - API Documentation: http://localhost:8000/api/docs/

## 🔧 Service Communication

### REST API Communication
Services communicate via HTTP REST APIs through the API Gateway or direct service-to-service calls.

**Example**: Academic Service validating student enrollment
```python
from users.clients import academic_client

result = academic_client.validate_course_enrollment(
    student_id=123, 
    course_id="CS101", 
    token=service_token
)
```

### Message Queue (Asynchronous)
For event-driven communication using Celery + Redis:

```python
from shared.message_queue import publish_user_created_event

# When a new user is created
publish_user_created_event(
    user_id=user.id,
    user_type=user.get_user_type_display(),
    user_data=serializer.data
)
```

### Authentication Flow
1. Client authenticates with User Management Service
2. Receives JWT token
3. API Gateway validates token for each request
4. Services can validate tokens independently

## 📊 Migration Strategy

### Phase 1: Foundation (✅ COMPLETED)
- [x] Extract User Management Service
- [x] Set up PostgreSQL database
- [x] Implement JWT authentication
- [x] Create API Gateway
- [x] Set up Docker infrastructure

### Phase 2: Core Services (📋 NEXT)
- [ ] Extract Academic Service
- [ ] Extract Attendance Service
- [ ] Update inter-service communication
- [ ] Migrate existing data

### Phase 3: Extended Services (📋 FUTURE)
- [ ] Extract Assessment Service
- [ ] Extract Notification Service
- [ ] Extract Leave Management Service
- [ ] Extract Feedback Service
- [ ] Extract Financial Service

### Phase 4: Optimization (📋 FUTURE)
- [ ] Implement service discovery
- [ ] Add monitoring and logging
- [ ] Performance optimization
- [ ] Security hardening

## 🔄 Data Migration

### User Management Service Migration
```bash
# Export data from monolith
python manage.py dumpdata student_management_app.CustomUser > users.json
python manage.py dumpdata student_management_app.Students > students.json
python manage.py dumpdata student_management_app.Staffs > staff.json
python manage.py dumpdata student_management_app.AdminHOD > admins.json

# Import to microservice
docker compose exec user-management python manage.py loaddata users.json
docker compose exec user-management python manage.py loaddata students.json
docker compose exec user-management python manage.py loaddata staff.json
docker compose exec user-management python manage.py loaddata admins.json
```

## 🛡️ Security Considerations

### Authentication & Authorization
- JWT tokens with configurable expiration
- Service-to-service authentication
- Role-based access control
- Session tracking for security

### Network Security
- Services communicate within Docker network
- API Gateway as single entry point
- HTTPS in production
- Rate limiting and request validation

### Data Security
- Encrypted database connections
- Secure environment variable management
- Audit logging
- Data validation at service boundaries

## 📈 Monitoring & Observability

### Health Checks
Each service provides health check endpoints:
- User Management: `GET /api/v1/users/health/`
- API Gateway: `GET /health`
- Service Status: `GET /api/v1/services/status`

### Logging
- Centralized logging with structured format
- Service-specific log levels
- Request/response logging
- Error tracking and alerting

### Metrics
- Service performance metrics
- Database connection monitoring
- Redis memory usage
- API response times

## 🔧 Development Workflow

### Adding a New Service
1. Create service directory structure
2. Implement Django REST API
3. Add database models and migrations
4. Create Docker configuration
5. Update API Gateway routing
6. Add service client utilities
7. Update docker compose.yml
8. Write tests and documentation

### Local Development
```bash
# Start infrastructure
docker compose up postgres redis

# Run service locally
cd user-management-service
python manage.py runserver 8000

# Run tests
python manage.py test
```

## 📚 API Documentation

### User Management Service
- **Swagger UI**: http://localhost:8000/api/docs/
- **OpenAPI Schema**: http://localhost:8000/api/schema/

### API Gateway
- **Service Status**: http://localhost:8080/api/v1/services/status
- **Health Check**: http://localhost:8080/health

## 🚨 Troubleshooting

### Common Issues

**Service Connection Errors**:
```bash
# Check service health
docker compose ps
docker compose logs user-management
```

**Database Connection Issues**:
```bash
# Check PostgreSQL
docker compose exec postgres psql -U postgres -d user_service_db
```

**Authentication Problems**:
```bash
# Validate JWT token
curl -H "Authorization: Bearer <token>" \
     http://localhost:8000/api/v1/users/validate-token/
```

## 📋 Next Steps

1. **Implement Academic Service** following the User Management Service pattern
2. **Set up data synchronization** between services
3. **Add comprehensive testing** for inter-service communication
4. **Implement monitoring** and alerting
5. **Plan production deployment** strategy

## 🤝 Contributing

1. Follow the established service patterns
2. Maintain API compatibility
3. Add comprehensive tests
4. Update documentation
5. Follow security best practices

---

**Status**: User Management Service extraction completed ✅  
**Next**: Academic Service implementation 📋  
**Architecture**: Microservices with API Gateway 🏗️
