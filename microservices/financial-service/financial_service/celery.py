import os

from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "financial_service.settings")

app = Celery("financial_service")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Periodic tasks
app.conf.beat_schedule = {
    "process-overdue-payments": {
        "task": "finances.tasks.process_overdue_payments",
        "schedule": 86400.0,  # Daily
    },
    "send-payment-reminders": {
        "task": "finances.tasks.send_payment_reminders",
        "schedule": 86400.0,  # Daily
    },
    "generate-financial-reports": {
        "task": "finances.tasks.generate_financial_reports",
        "schedule": 604800.0,  # Weekly
    },
    "cleanup-expired-transactions": {
        "task": "finances.tasks.cleanup_expired_transactions",
        "schedule": 2592000.0,  # Monthly
    },
    "sync-payment-gateway-status": {
        "task": "finances.tasks.sync_payment_gateway_status",
        "schedule": 3600.0,  # Hourly
    },
}
