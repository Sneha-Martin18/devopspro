"""
Signals for the notifications app.
"""
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Notification, NotificationStatus
from .tasks import send_notification

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Notification)
def handle_notification_creation(sender, instance, created, **kwargs):
    """
    Handle notification creation by scheduling it for sending.
    """
    if created and instance.status == NotificationStatus.PENDING:
        # If scheduled for future, schedule the task for that time
        if instance.scheduled_at and instance.scheduled_at > timezone.now():
            send_notification.apply_async(
                args=[str(instance.id)], eta=instance.scheduled_at
            )
            logger.info(
                f"Scheduled notification {instance.id} for {instance.scheduled_at}"
            )
        else:
            # Send immediately
            send_notification.delay(str(instance.id))
            logger.info(f"Queued notification {instance.id} for immediate sending")
