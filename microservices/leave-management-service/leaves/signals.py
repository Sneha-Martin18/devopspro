from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import LeaveApproval, LeaveRequest
from .tasks import process_leave_approval, send_leave_notification


@receiver(post_save, sender=LeaveRequest)
def handle_leave_request_created(sender, instance, created, **kwargs):
    """Handle leave request creation and status changes"""
    if created:
        # Send notification when leave request is created
        send_leave_notification.delay(instance.id, "SUBMITTED", instance.user_email)
    else:
        # Handle status changes
        if hasattr(instance, "_status_changed") and instance._status_changed:
            if instance.status == "APPROVED":
                process_leave_approval.delay(instance.id, "APPROVED")
            elif instance.status == "CANCELLED":
                process_leave_approval.delay(instance.id, "CANCELLED")


@receiver(pre_save, sender=LeaveRequest)
def track_leave_request_changes(sender, instance, **kwargs):
    """Track changes to leave request status"""
    if instance.pk:
        try:
            old_instance = LeaveRequest.objects.get(pk=instance.pk)
            instance._status_changed = old_instance.status != instance.status
        except LeaveRequest.DoesNotExist:
            instance._status_changed = False
    else:
        instance._status_changed = False
