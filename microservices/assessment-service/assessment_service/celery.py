import os

from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "assessment_service.settings")

app = Celery("assessment_service")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Periodic tasks
app.conf.beat_schedule = {
    "process-overdue-assignments": {
        "task": "assessments.tasks.process_overdue_assignments",
        "schedule": 3600.0,  # Every hour
    },
    "send-assignment-reminders": {
        "task": "assessments.tasks.send_assignment_reminders",
        "schedule": 86400.0,  # Daily
    },
    "generate-grade-reports": {
        "task": "assessments.tasks.generate_grade_reports",
        "schedule": 604800.0,  # Weekly
    },
    "cleanup-old-submissions": {
        "task": "assessments.tasks.cleanup_old_submissions",
        "schedule": 2592000.0,  # Monthly
    },
}
