SERVICE_ROUTES = {
    # Core Services
    'dashboard': 'http://localhost:8000',
    'admin': 'http://localhost:8000/admin',
    
    # User Management
    'student': 'http://localhost:8000/student',
    'staff': 'http://localhost:8000/staff',
    'auth': 'http://localhost:8000/auth',
    
    # Academic Services
    'courses': 'http://localhost:8000/courses',
    'subjects': 'http://localhost:8000/subjects',
    'attendance': 'http://localhost:8000/attendance',
    'assignments': 'http://localhost:8000/assignments',
    'results': 'http://localhost:8000/results',
    
    # Administrative Services
    'leave': 'http://localhost:8000/leave',
    'feedback': 'http://localhost:8000/feedback',
    'notifications': 'http://localhost:8000/notifications',
    
    # Financial Services
    'fees': 'http://localhost:8000/fees',
    'payments': 'http://localhost:8000/payments',
    
    # API Services
    'api': 'http://localhost:8000/api'
}

# Configuration
DEFAULT_TIMEOUT = 30  # seconds
DEFAULT_PORT = 8000
BASE_URL = f'http://localhost:{DEFAULT_PORT}'

# Service Groups
ACADEMIC_SERVICES = ['courses', 'subjects', 'attendance', 'assignments', 'results']
ADMIN_SERVICES = ['leave', 'feedback', 'notifications']
USER_SERVICES = ['student', 'staff', 'auth']
FINANCIAL_SERVICES = ['fees', 'payments']

# Feature Flags
ENABLE_CACHING = True
ENABLE_RATE_LIMITING = True
ENABLE_AUTH_CHECK = True
