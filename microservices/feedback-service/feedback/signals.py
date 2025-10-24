from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Feedback, FeedbackResponse
from .tasks import analyze_feedback_sentiment, send_feedback_notification


@receiver(post_save, sender=Feedback)
def handle_feedback_created(sender, instance, created, **kwargs):
    """Handle feedback creation and status changes"""
    if created:
        # Send notification when feedback is created
        send_feedback_notification.delay(
            instance.id,
            "SUBMITTED",
            instance.user_email if not instance.is_anonymous else None,
        )

        # Analyze sentiment asynchronously
        analyze_feedback_sentiment.delay()
    else:
        # Handle status changes
        if hasattr(instance, "_status_changed") and instance._status_changed:
            send_feedback_notification.delay(
                instance.id,
                instance.status,
                instance.user_email if not instance.is_anonymous else None,
            )


@receiver(pre_save, sender=Feedback)
def track_feedback_changes(sender, instance, **kwargs):
    """Track changes to feedback status"""
    if instance.pk:
        try:
            old_instance = Feedback.objects.get(pk=instance.pk)
            instance._status_changed = old_instance.status != instance.status
        except Feedback.DoesNotExist:
            instance._status_changed = False
    else:
        instance._status_changed = False


@receiver(post_save, sender=FeedbackResponse)
def handle_response_created(sender, instance, created, **kwargs):
    """Handle feedback response creation"""
    if created:
        # Send notification to feedback author
        send_feedback_notification.delay(
            instance.feedback.id,
            "RESPONSE_ADDED",
            instance.feedback.user_email
            if not instance.feedback.is_anonymous
            else None,
        )
