"""
Serializers for the notifications app.
"""
from django.utils import timezone
from rest_framework import serializers

from .models import (Notification, NotificationChannel, NotificationLog,
                     NotificationPreference, NotificationPriority,
                     NotificationStatus, NotificationTemplate)


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """Serializer for NotificationTemplate model."""

    class Meta:
        model = NotificationTemplate
        fields = [
            "id",
            "name",
            "description",
            "channel",
            "subject_template",
            "message_template",
            "html_template",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        """Validate template name is unique."""
        if self.instance and self.instance.name == value:
            return value
        if NotificationTemplate.objects.filter(name=value).exists():
            raise serializers.ValidationError("Template with this name already exists.")
        return value


class NotificationLogSerializer(serializers.ModelSerializer):
    """Serializer for NotificationLog model."""

    class Meta:
        model = NotificationLog
        fields = ["id", "status", "message", "provider_response", "created_at"]
        read_only_fields = ["id", "created_at"]


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model."""

    template_name = serializers.CharField(source="template.name", read_only=True)
    logs = NotificationLogSerializer(many=True, read_only=True)
    is_read = serializers.BooleanField(read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "recipient_id",
            "email",
            "phone_number",
            "channel",
            "status",
            "priority",
            "template",
            "template_name",
            "subject",
            "message",
            "html_message",
            "context",
            "scheduled_at",
            "sent_at",
            "delivered_at",
            "read_at",
            "retry_count",
            "max_retries",
            "error_message",
            "is_read",
            "logs",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "sent_at",
            "delivered_at",
            "retry_count",
            "error_message",
            "created_at",
            "updated_at",
        ]

    def validate(self, data):
        """Validate notification data based on channel."""
        channel = data.get("channel")

        if channel == NotificationChannel.EMAIL:
            if not data.get("email"):
                raise serializers.ValidationError(
                    "Email address is required for email notifications."
                )
        elif channel == NotificationChannel.SMS:
            if not data.get("phone_number"):
                raise serializers.ValidationError(
                    "Phone number is required for SMS notifications."
                )

        # Validate scheduled_at is not in the past
        scheduled_at = data.get("scheduled_at")
        if scheduled_at and scheduled_at < timezone.now():
            raise serializers.ValidationError("Scheduled time cannot be in the past.")

        return data


class CreateNotificationSerializer(serializers.ModelSerializer):
    """Serializer for creating notifications."""

    template_id = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = Notification
        fields = [
            "recipient_id",
            "email",
            "phone_number",
            "channel",
            "priority",
            "template_id",
            "subject",
            "message",
            "html_message",
            "context",
            "scheduled_at",
            "max_retries",
        ]

    def validate(self, data):
        """Validate notification creation data."""
        channel = data.get("channel")

        if channel == NotificationChannel.EMAIL:
            if not data.get("email"):
                raise serializers.ValidationError(
                    "Email address is required for email notifications."
                )
        elif channel == NotificationChannel.SMS:
            if not data.get("phone_number"):
                raise serializers.ValidationError(
                    "Phone number is required for SMS notifications."
                )

        # Validate scheduled_at
        scheduled_at = data.get("scheduled_at")
        if scheduled_at and scheduled_at < timezone.now():
            raise serializers.ValidationError("Scheduled time cannot be in the past.")

        return data

    def create(self, validated_data):
        """Create a new notification."""
        template_id = validated_data.pop("template_id", None)

        if template_id:
            try:
                template = NotificationTemplate.objects.get(
                    id=template_id, is_active=True
                )
                validated_data["template"] = template
            except NotificationTemplate.DoesNotExist:
                raise serializers.ValidationError("Invalid or inactive template ID.")

        return Notification.objects.create(**validated_data)


class BulkCreateNotificationSerializer(serializers.Serializer):
    """Serializer for creating multiple notifications."""

    recipient_ids = serializers.ListField(
        child=serializers.CharField(max_length=100), min_length=1, max_length=1000
    )
    channel = serializers.ChoiceField(choices=NotificationChannel.choices)
    priority = serializers.ChoiceField(
        choices=NotificationPriority.choices, default=NotificationPriority.NORMAL
    )
    template_id = serializers.UUIDField(required=False, allow_null=True)
    subject = serializers.CharField(max_length=255, required=False, allow_blank=True)
    message = serializers.CharField(required=True)
    html_message = serializers.CharField(required=False, allow_blank=True)
    context = serializers.JSONField(default=dict)
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True)
    max_retries = serializers.IntegerField(default=3, min_value=0, max_value=10)

    def validate_scheduled_at(self, value):
        """Validate scheduled_at is not in the past."""
        if value and value < timezone.now():
            raise serializers.ValidationError("Scheduled time cannot be in the past.")
        return value

    def create(self, validated_data):
        """Create multiple notifications."""
        recipient_ids = validated_data.pop("recipient_ids")
        template_id = validated_data.pop("template_id", None)

        template = None
        if template_id:
            try:
                template = NotificationTemplate.objects.get(
                    id=template_id, is_active=True
                )
            except NotificationTemplate.DoesNotExist:
                raise serializers.ValidationError("Invalid or inactive template ID.")

        notifications = []
        for recipient_id in recipient_ids:
            notification_data = validated_data.copy()
            notification_data["recipient_id"] = recipient_id
            notification_data["template"] = template

            # Set email/phone based on channel and recipient preferences
            if notification_data["channel"] == NotificationChannel.EMAIL:
                try:
                    pref = NotificationPreference.objects.get(user_id=recipient_id)
                    notification_data["email"] = pref.email_address
                except NotificationPreference.DoesNotExist:
                    pass
            elif notification_data["channel"] == NotificationChannel.SMS:
                try:
                    pref = NotificationPreference.objects.get(user_id=recipient_id)
                    notification_data["phone_number"] = pref.phone_number
                except NotificationPreference.DoesNotExist:
                    pass

            notifications.append(Notification(**notification_data))

        return Notification.objects.bulk_create(notifications)


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for NotificationPreference model."""

    class Meta:
        model = NotificationPreference
        fields = [
            "id",
            "user_id",
            "email_enabled",
            "sms_enabled",
            "in_app_enabled",
            "push_enabled",
            "email_address",
            "phone_number",
            "do_not_disturb_start",
            "do_not_disturb_end",
            "timezone",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_user_id(self, value):
        """Validate user_id is unique."""
        if self.instance and self.instance.user_id == value:
            return value
        if NotificationPreference.objects.filter(user_id=value).exists():
            raise serializers.ValidationError(
                "Preferences for this user already exist."
            )
        return value


class UpdateNotificationStatusSerializer(serializers.Serializer):
    """Serializer for updating notification status."""

    status = serializers.ChoiceField(choices=NotificationStatus.choices)
    error_message = serializers.CharField(required=False, allow_blank=True)
