"""
Models for the notifications app.
"""
import uuid

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class NotificationChannel(models.TextChoices):
    EMAIL = "email", "Email"
    SMS = "sms", "SMS"
    IN_APP = "in_app", "In-App"
    PUSH = "push", "Push Notification"


class NotificationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    SENT = "sent", "Sent"
    DELIVERED = "delivered", "Delivered"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"


class NotificationPriority(models.TextChoices):
    LOW = "low", "Low"
    NORMAL = "normal", "Normal"
    HIGH = "high", "High"
    URGENT = "urgent", "Urgent"


class NotificationTemplate(models.Model):
    """Template for reusable notifications."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    channel = models.CharField(max_length=20, choices=NotificationChannel.choices)
    subject_template = models.CharField(max_length=255, blank=True)
    message_template = models.TextField()
    html_template = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notification_templates"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.channel})"


class Notification(models.Model):
    """Individual notification to be sent."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient_id = models.CharField(max_length=100)  # User ID from other services
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=20, blank=True)

    channel = models.CharField(max_length=20, choices=NotificationChannel.choices)
    status = models.CharField(
        max_length=20,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING,
    )
    priority = models.CharField(
        max_length=20,
        choices=NotificationPriority.choices,
        default=NotificationPriority.NORMAL,
    )

    template = models.ForeignKey(
        NotificationTemplate, on_delete=models.SET_NULL, null=True, blank=True
    )
    subject = models.CharField(max_length=255, blank=True)
    message = models.TextField()
    html_message = models.TextField(blank=True)
    context = models.JSONField(default=dict, blank=True)

    scheduled_at = models.DateTimeField(default=timezone.now)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    retry_count = models.PositiveIntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=3)
    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient_id", "status"]),
            models.Index(fields=["channel", "status"]),
            models.Index(fields=["scheduled_at"]),
            models.Index(fields=["priority", "status"]),
        ]

    def __str__(self):
        return f"Notification to {self.recipient_id} via {self.channel}"

    @property
    def is_read(self):
        return self.read_at is not None

    def mark_as_read(self):
        if not self.read_at:
            self.read_at = timezone.now()
            self.save(update_fields=["read_at"])


class NotificationPreference(models.Model):
    """User preferences for notifications."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.CharField(
        max_length=100, unique=True
    )  # User ID from other services

    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    in_app_enabled = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=True)

    email_address = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=20, blank=True)

    do_not_disturb_start = models.TimeField(null=True, blank=True)
    do_not_disturb_end = models.TimeField(null=True, blank=True)
    timezone = models.CharField(max_length=50, default="UTC")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notification_preferences"

    def __str__(self):
        return f"Preferences for user {self.user_id}"


class NotificationLog(models.Model):
    """Log of notification delivery attempts."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.ForeignKey(
        Notification, on_delete=models.CASCADE, related_name="logs"
    )
    status = models.CharField(max_length=20, choices=NotificationStatus.choices)
    message = models.TextField()
    provider_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notification_logs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Log for {self.notification.id} - {self.status}"
