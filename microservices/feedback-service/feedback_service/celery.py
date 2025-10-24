import os

from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "feedback_service.settings")

app = Celery("feedback_service")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Periodic tasks
app.conf.beat_schedule = {
    "process-pending-feedback": {
        "task": "feedback.tasks.process_pending_feedback",
        "schedule": 60.0 * 60,  # Hourly
    },
    "generate-feedback-reports": {
        "task": "feedback.tasks.generate_feedback_reports",
        "schedule": 60.0 * 60 * 24,  # Daily
    },
    "cleanup-old-feedback": {
        "task": "feedback.tasks.cleanup_old_feedback",
        "schedule": 60.0 * 60 * 24 * 7,  # Weekly
    },
}

app.conf.timezone = "Asia/Kolkata"


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
