from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Assignment, Grade, StudentResult, Submission
from .tasks import (process_grade_calculation, send_assignment_notification,
                    send_grade_notifications)


@receiver(post_save, sender=Assignment)
def handle_assignment_created(sender, instance, created, **kwargs):
    """Handle assignment creation and status changes"""
    if created:
        # Send notification when assignment is created
        send_assignment_notification.delay(instance.id, "CREATED")
    else:
        # Handle status changes
        if hasattr(instance, "_status_changed") and instance._status_changed:
            if instance.status == "PUBLISHED":
                send_assignment_notification.delay(instance.id, "PUBLISHED")
            elif instance.status == "CLOSED":
                send_assignment_notification.delay(instance.id, "CLOSED")


@receiver(pre_save, sender=Assignment)
def track_assignment_changes(sender, instance, **kwargs):
    """Track changes to assignment status"""
    if instance.pk:
        try:
            old_instance = Assignment.objects.get(pk=instance.pk)
            instance._status_changed = old_instance.status != instance.status
        except Assignment.DoesNotExist:
            instance._status_changed = False
    else:
        instance._status_changed = False


@receiver(post_save, sender=Submission)
def handle_submission_created(sender, instance, created, **kwargs):
    """Handle submission creation and grading"""
    if created:
        # Update assignment submission count
        assignment = instance.assignment
        assignment.submission_count = assignment.submissions.count()
        assignment.save(update_fields=["submission_count"])

    # If submission is graded, trigger grade calculation
    if instance.status == "GRADED" and instance.marks_obtained is not None:
        process_grade_calculation.delay(
            instance.student_id, instance.assignment.course_id
        )


@receiver(post_save, sender=Grade)
def handle_grade_created(sender, instance, created, **kwargs):
    """Handle grade creation and updates"""
    if created:
        # Send notification to student
        send_grade_notifications.delay(instance.id)

        # Trigger result calculation
        process_grade_calculation.delay(instance.student_id, instance.course_id)


@receiver(post_save, sender=StudentResult)
def handle_result_published(sender, instance, created, **kwargs):
    """Handle result publication"""
    if (
        not created
        and hasattr(instance, "_status_changed")
        and instance._status_changed
    ):
        if instance.result_status == "PUBLISHED":
            # Send result notification
            from .tasks import send_assignment_notification

            # Could create a separate task for result notifications
            pass


@receiver(pre_save, sender=StudentResult)
def track_result_changes(sender, instance, **kwargs):
    """Track changes to result status"""
    if instance.pk:
        try:
            old_instance = StudentResult.objects.get(pk=instance.pk)
            instance._status_changed = (
                old_instance.result_status != instance.result_status
            )
        except StudentResult.DoesNotExist:
            instance._status_changed = False
    else:
        instance._status_changed = False
