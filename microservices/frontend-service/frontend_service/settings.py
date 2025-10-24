import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv(
    "SECRET_KEY", "django-insecure-frontend-key-change-in-production"
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

ALLOWED_HOSTS = ["*"]

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "frontend",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "frontend.middleware.AuthenticationMiddleware",
]

ROOT_URLCONF = "frontend_service.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            # Point to original templates from student_management_app
            "/app/original_templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "frontend_service.wsgi.application"

# Database - Using SQLite for frontend session storage only
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# Point to mounted static files
STATICFILES_DIRS = [
    "/app/static_files",
]

# Static files serving in development
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# API Gateway Configuration
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://api-gateway:8080")

# Service URLs (for direct communication if needed)
SERVICE_URLS = {
    "user_management": os.getenv("USER_SERVICE_URL", "http://user-management:8000"),
    "academic": os.getenv("ACADEMIC_SERVICE_URL", "http://academic:8001"),
    "attendance": os.getenv("ATTENDANCE_SERVICE_URL", "http://attendance:8002"),
    "notification": os.getenv("NOTIFICATION_SERVICE_URL", "http://notification:8003"),
    "leave_management": os.getenv("LEAVE_SERVICE_URL", "http://leave-management:8004"),
    "feedback": os.getenv("FEEDBACK_SERVICE_URL", "http://feedback:8005"),
    "assessment": os.getenv("ASSESSMENT_SERVICE_URL", "http://assessment:8006"),
    "financial": os.getenv("FINANCIAL_SERVICE_URL", "http://financial:8007"),
}

# CORS settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

CORS_ALLOW_ALL_ORIGINS = DEBUG

# Session configuration
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_SAVE_EVERY_REQUEST = True

# Custom authentication backend for API integration
AUTHENTICATION_BACKENDS = [
    "frontend.backends.APIGatewayBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# CSRF Settings
CSRF_USE_SESSIONS = False
CSRF_COOKIE_HTTPONLY = False  # Required for JavaScript to access CSRF token
CSRF_COOKIE_SECURE = False  # Set to True in production with HTTPS
CSRF_TRUSTED_ORIGINS = os.getenv(
    "CSRF_TRUSTED_ORIGINS", "http://localhost:9000,http://127.0.0.1:9000"
).split(",")
CSRF_COOKIE_DOMAIN = os.getenv("CSRF_COOKIE_DOMAIN", None)
CSRF_HEADER_NAME = "HTTP_X_CSRFTOKEN"
CSRF_COOKIE_NAME = "csrftoken"
CSRF_FAILURE_VIEW = "frontend.views.csrf_failure"
CSRF_COOKIE_SAMESITE = "Lax"

# Session Settings
SESSION_ENGINE = "django.contrib.sessions.backends.db"  # Use database-backed sessions
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
SESSION_COOKIE_AGE = 1209600  # 2 weeks, in seconds
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_SAMESITE = "Lax"  # Helps with CSRF protection
SESSION_COOKIE_NAME = "sessionid_frontend"
SESSION_COOKIE_DOMAIN = None  # Set to your domain in production

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "frontend": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
