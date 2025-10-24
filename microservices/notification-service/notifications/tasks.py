"""
Celery tasks for the notifications app.
"""
import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail as django_send_mail
from django.utils import timezone
from twilio.rest import Client as TwilioClient

from .models import Notification, NotificationLog, NotificationStatus

logger = logging.getLogger(__name__)

# Initialize Twilio client if credentials are available
try:
    TWILIO_CLIENT = (
        TwilioClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        if all(
            [
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN,
                settings.TWILIO_PHONE_NUMBER,
            ]
        )
        else None
    )
except Exception as e:
    logger.warning(f"Failed to initialize Twilio client: {str(e)}")
    TWILIO_CLIENT = None


def create_notification_log(notification, status, message, response=None):
    """Helper to create a notification log entry."""
    return NotificationLog.objects.create(
        notification=notification,
        status=status,
        message=message,
        provider_response=response or {},
    )


@shared_task(bind=True, max_retries=3)
def send_notification(self, notification_id):
    """Send a single notification asynchronously."""
    try:
        notification = Notification.objects.get(id=notification_id)

        if notification.status in [
            NotificationStatus.SENT,
            NotificationStatus.DELIVERED,
        ]:
            logger.info(f"Notification {notification_id} already sent/delivered")
            return

        if notification.scheduled_at > timezone.now():
            logger.info(
                f"Notification {notification_id} scheduled for future, rescheduling..."
            )
            send_notification.apply_async(
                args=[notification_id], eta=notification.scheduled_at
            )
            return

        notification.status = "processing"
        notification.save(update_fields=["status", "updated_at"])

        try:
            if notification.channel == "email":
                success, error = send_email(notification)
            elif notification.channel == "sms":
                success, error = send_sms(notification)
            else:
                success, error = send_in_app(notification)

            if success:
                notification.status = NotificationStatus.DELIVERED
                notification.sent_at = timezone.now()
                notification.delivered_at = timezone.now()
                create_notification_log(
                    notification,
                    NotificationStatus.DELIVERED,
                    "Notification delivered successfully",
                )
            else:
                notification.status = NotificationStatus.FAILED
                notification.error_message = error
                create_notification_log(
                    notification,
                    NotificationStatus.FAILED,
                    f"Failed to send notification: {error}",
                )

                if notification.retry_count < notification.max_retries:
                    notification.retry_count += 1
                    notification.status = NotificationStatus.PENDING
                    send_notification.apply_async(
                        args=[notification_id], countdown=60 * notification.retry_count
                    )

            notification.save()

        except Exception as e:
            error_msg = f"Error sending notification: {str(e)}"
            logger.exception(error_msg)
            notification.status = NotificationStatus.FAILED
            notification.error_message = error_msg
            notification.save()
            raise self.retry(exc=e, countdown=60 * (notification.retry_count or 1))

    except Notification.DoesNotExist:
        logger.error(f"Notification {notification_id} not found")
    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")


def send_email(notification):
    """Send an email notification."""
    try:
        subject = notification.subject or ""
        message = notification.message or ""
        html_message = notification.html_message or ""

        django_send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[notification.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True, None
    except Exception as e:
        return False, str(e)


def send_sms(notification):
    """Send an SMS via Twilio."""
    if not TWILIO_CLIENT:
        return False, "Twilio not configured"

    try:
        message = notification.message or ""
        twilio_message = TWILIO_CLIENT.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=notification.phone_number,
        )

        create_notification_log(
            notification,
            NotificationStatus.SENT,
            "SMS sent successfully",
            response={
                "sid": twilio_message.sid,
                "status": twilio_message.status,
                "to": twilio_message.to,
            },
        )
        return True, None
    except Exception as e:
        return False, str(e)


def send_in_app(notification):
    """Handle in-app notifications."""
    try:
        logger.info(
            f"In-app notification to {notification.recipient_id}: {notification.message}"
        )
        return True, None
    except Exception as e:
        return False, str(e)


@shared_task
def cleanup_old_notifications(days=30):
    """Clean up old delivered notifications."""
    try:
        cutoff = timezone.now() - timezone.timedelta(days=days)
        deleted, _ = Notification.objects.filter(
            status=NotificationStatus.DELIVERED, delivered_at__lt=cutoff
        ).delete()
        logger.info(f"Cleaned up {deleted} old notifications")
        return deleted
    except Exception as e:
        logger.exception(f"Error cleaning up notifications: {str(e)}")
        return 0


@shared_task
def send_bulk_notifications(notification_data):
    """Send multiple notifications in bulk."""
    try:
        from .serializers import BulkCreateNotificationSerializer

        serializer = BulkCreateNotificationSerializer(data=notification_data)
        if serializer.is_valid():
            notifications = serializer.save()
            logger.info(f"Created {len(notifications)} bulk notifications")
            return len(notifications)
        else:
            logger.error(f"Bulk notification validation failed: {serializer.errors}")
            return 0
    except Exception as e:
        logger.exception(f"Error creating bulk notifications: {str(e)}")
        return 0
