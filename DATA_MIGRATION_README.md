# Data Migration Guide: SQLite to PostgreSQL Microservices

This guide explains how to migrate all data from the original `db.sqlite3` file to the new PostgreSQL microservices architecture.

## Overview

The Django Student Management System has been migrated from a monolithic architecture using SQLite to a microservices architecture using PostgreSQL. This migration transfers all existing data to the appropriate microservice databases.

## Data Mapping

The original SQLite tables are mapped to the following microservice databases:

### User Management Service (`user_service_db`)
- `auth_user` - Django's built-in user table
- `student_management_app_customuser` - Custom user model
- `student_management_app_adminhod` - HOD/Admin profiles
- `student_management_app_staffs` - Staff profiles
- `student_management_app_students` - Student profiles

### Academic Service (`academic_service_db`)
- `student_management_app_sessionyearmodel` - Academic session years
- `student_management_app_courses` - Course information
- `student_management_app_subjects` - Subject information

### Attendance Service (`attendance_service_db`)
- `student_management_app_attendance` - Attendance sessions
- `student_management_app_attendancereport` - Individual attendance records

### Leave Management Service (`leave_management_db`)
- `student_management_app_leavereportstudent` - Student leave requests
- `student_management_app_leavereportstaff` - Staff leave requests

### Feedback Service (`feedback_service_db`)
- `student_management_app_feedbackstudent` - Student feedback
- `student_management_app_feedbackstaffs` - Staff feedback

### Notification Service (`notification_service_db`)
- `student_management_app_notificationstudent` - Student notifications
- `student_management_app_notificationstaffs` - Staff notifications

### Assessment Service (`assessment_service_db`)
- `student_management_app_studentresult` - Student results
- `student_management_app_assignment` - Assignment information
- `student_management_app_assignmentsubmission` - Assignment submissions

### Financial Service (`financial_service_db`)
- `student_management_app_fine` - Fine records
- `student_management_app_finepayment` - Payment records

## Prerequisites

1. **Original SQLite Database**: Ensure `db.sqlite3` exists in the project root
2. **Docker & Docker Compose**: Required for running microservices
3. **Python 3**: Required for running migration scripts
4. **PostgreSQL Client**: psycopg2-binary (installed automatically)

## Quick Migration (Automated)

The easiest way to migrate your data is using the automated setup script:

```bash
# Make the script executable
chmod +x setup_and_migrate.sh

# Run the complete setup and migration
./setup_and_migrate.sh
```

This script will:
1. ✅ Check all dependencies
2. ✅ Install Python requirements
3. ✅ Start all microservices
4. ✅ Create PostgreSQL databases
5. ✅ Run Django migrations
6. ✅ Migrate data from SQLite
7. ✅ Verify migration success

## Manual Migration (Step by Step)

If you prefer to run the migration manually:

### Step 1: Install Dependencies
```bash
pip3 install -r migration_requirements.txt
```

### Step 2: Start Microservices
```bash
cd microservices
docker compose up --build -d
```

### Step 3: Create Databases
```bash
# Connect to PostgreSQL and create databases
docker compose exec postgres psql -U postgres -c "CREATE DATABASE user_service_db;"
docker compose exec postgres psql -U postgres -c "CREATE DATABASE academic_service_db;"
docker compose exec postgres psql -U postgres -c "CREATE DATABASE attendance_service_db;"
docker compose exec postgres psql -U postgres -c "CREATE DATABASE notification_service_db;"
docker compose exec postgres psql -U postgres -c "CREATE DATABASE leave_management_db;"
docker compose exec postgres psql -U postgres -c "CREATE DATABASE feedback_service_db;"
docker compose exec postgres psql -U postgres -c "CREATE DATABASE assessment_service_db;"
docker compose exec postgres psql -U postgres -c "CREATE DATABASE financial_service_db;"
```

### Step 4: Run Django Migrations
```bash
# Run migrations for each service
docker compose exec user-management python manage.py migrate
docker compose exec academic python manage.py migrate
docker compose exec attendance python manage.py migrate
docker compose exec notification python manage.py migrate
docker compose exec leave-management python manage.py migrate
docker compose exec feedback python manage.py migrate
docker compose exec assessment python manage.py migrate
docker compose exec financial python manage.py migrate
```

### Step 5: Run Data Migration
```bash
cd ..
python3 migrate_data.py
```

## Migration Script Features

The `migrate_data.py` script includes:

- **Automatic Table Detection**: Scans SQLite database for all tables
- **Smart Type Mapping**: Maps SQLite types to PostgreSQL types
- **Data Validation**: Handles NULL values and empty strings
- **Progress Tracking**: Shows migration progress for each table
- **Verification**: Compares record counts between source and destination
- **Error Handling**: Graceful error handling with rollback support

## Verification

After migration, the script automatically verifies data integrity by:

1. Comparing record counts between SQLite and PostgreSQL
2. Checking database connections
3. Validating table structures

## Access Information

After successful migration, you can access:

- **Frontend**: http://localhost:9000
- **API Gateway**: http://localhost:8080
- **API Documentation**: http://localhost:8080/docs

### Default Admin Credentials
If admin user was migrated:
- **Email**: admin@gmail.com
- **Password**: admin
- **User Type**: HOD/Admin

## Troubleshooting

### Common Issues

1. **SQLite file not found**
   - Ensure `db.sqlite3` exists in the project root
   - Check file permissions

2. **PostgreSQL connection failed**
   - Ensure microservices are running: `docker compose ps`
   - Check PostgreSQL health: `docker compose exec postgres pg_isready`

3. **Migration script fails**
   - Check Python dependencies: `pip3 list | grep psycopg2`
   - Verify database connections
   - Check Docker container logs: `docker compose logs`

4. **Data mismatch after migration**
   - Review migration logs for errors
   - Check for foreign key constraint issues
   - Verify table mappings in the script

### Manual Verification

To manually verify migration:

```bash
# Check SQLite record count
sqlite3 db.sqlite3 "SELECT COUNT(*) FROM student_management_app_customuser;"

# Check PostgreSQL record count
docker compose exec postgres psql -U postgres -d user_service_db -c "SELECT COUNT(*) FROM student_management_app_customuser;"
```

## File Structure

```
project/
├── db.sqlite3                     # Original SQLite database
├── migrate_data.py                # Main migration script
├── migration_requirements.txt     # Python dependencies
├── setup_and_migrate.sh          # Automated setup script
├── DATA_MIGRATION_README.md       # This guide
└── microservices/
    ├── docker compose.yml         # Microservices configuration
    └── [service directories...]
```

## Support

If you encounter issues during migration:

1. Check the migration logs for specific error messages
2. Verify all microservices are healthy
3. Ensure the original SQLite database is accessible
4. Review the data mapping configuration in `migrate_data.py`

The migration process preserves all relationships and data integrity while distributing data across the appropriate microservice databases.
