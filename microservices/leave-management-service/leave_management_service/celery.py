import os

from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "leave_management_service.settings")

app = Celery("leave_management_service")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Periodic tasks
app.conf.beat_schedule = {
    "send-leave-reminders": {
        "task": "leaves.tasks.send_leave_reminders",
        "schedule": 60.0 * 60 * 24,  # Daily
    },
    "cleanup-old-leave-data": {
        "task": "leaves.tasks.cleanup_old_leave_data",
        "schedule": 60.0 * 60 * 24 * 7,  # Weekly
    },
}

app.conf.timezone = "Asia/Kolkata"


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
