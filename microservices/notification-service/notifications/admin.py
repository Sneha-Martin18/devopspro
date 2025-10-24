"""
Admin configuration for the notifications app.
"""
from django.contrib import admin
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import (Notification, NotificationLog, NotificationPreference,
                     NotificationTemplate)


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "channel", "is_active", "created_at"]
    list_filter = ["channel", "is_active", "created_at"]
    search_fields = ["name", "description"]
    readonly_fields = ["id", "created_at", "updated_at"]
    fieldsets = (
        (None, {"fields": ("name", "description", "channel", "is_active")}),
        (
            "Templates",
            {"fields": ("subject_template", "message_template", "html_template")},
        ),
        (
            "Metadata",
            {"fields": ("id", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


class NotificationLogInline(admin.TabularInline):
    model = NotificationLog
    extra = 0
    readonly_fields = ["status", "message", "provider_response", "created_at"]
    can_delete = False


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        "recipient_id",
        "channel",
        "status",
        "priority",
        "scheduled_at",
        "sent_at",
        "is_read",
        "retry_count",
    ]
    list_filter = [
        "status",
        "channel",
        "priority",
        "created_at",
        "scheduled_at",
        "sent_at",
    ]
    search_fields = ["recipient_id", "email", "phone_number", "subject", "message"]
    readonly_fields = [
        "id",
        "sent_at",
        "delivered_at",
        "read_at",
        "retry_count",
        "created_at",
        "updated_at",
    ]
    inlines = [NotificationLogInline]

    fieldsets = (
        ("Recipient", {"fields": ("recipient_id", "email", "phone_number")}),
        (
            "Notification Details",
            {"fields": ("channel", "status", "priority", "template")},
        ),
        ("Content", {"fields": ("subject", "message", "html_message", "context")}),
        (
            "Scheduling & Delivery",
            {
                "fields": (
                    "scheduled_at",
                    "sent_at",
                    "delivered_at",
                    "read_at",
                    "max_retries",
                    "retry_count",
                    "error_message",
                )
            },
        ),
        (
            "Metadata",
            {"fields": ("id", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    actions = ["mark_as_read", "retry_failed_notifications"]

    def mark_as_read(self, request, queryset):
        """Mark selected notifications as read."""
        updated = 0
        for notification in queryset:
            if not notification.is_read:
                notification.mark_as_read()
                updated += 1
        self.message_user(request, f"{updated} notifications marked as read.")

    mark_as_read.short_description = "Mark selected notifications as read"

    def retry_failed_notifications(self, request, queryset):
        """Retry failed notifications."""
        from .tasks import send_notification

        retried = 0
        for notification in queryset.filter(status="failed"):
            if notification.retry_count < notification.max_retries:
                notification.status = "pending"
                notification.error_message = ""
                notification.save(update_fields=["status", "error_message"])
                send_notification.delay(str(notification.id))
                retried += 1

        self.message_user(request, f"{retried} notifications queued for retry.")

    retry_failed_notifications.short_description = "Retry failed notifications"


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = [
        "user_id",
        "email_enabled",
        "sms_enabled",
        "in_app_enabled",
        "push_enabled",
        "created_at",
    ]
    list_filter = [
        "email_enabled",
        "sms_enabled",
        "in_app_enabled",
        "push_enabled",
        "created_at",
    ]
    search_fields = ["user_id", "email_address", "phone_number"]
    readonly_fields = ["id", "created_at", "updated_at"]

    fieldsets = (
        ("User", {"fields": ("user_id",)}),
        (
            "Channel Preferences",
            {
                "fields": (
                    "email_enabled",
                    "sms_enabled",
                    "in_app_enabled",
                    "push_enabled",
                )
            },
        ),
        ("Contact Information", {"fields": ("email_address", "phone_number")}),
        (
            "Do Not Disturb",
            {"fields": ("do_not_disturb_start", "do_not_disturb_end", "timezone")},
        ),
        (
            "Metadata",
            {"fields": ("id", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ["notification_link", "status", "message", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["notification__recipient_id", "message"]
    readonly_fields = [
        "notification",
        "status",
        "message",
        "provider_response",
        "created_at",
    ]

    def notification_link(self, obj):
        """Create a link to the related notification."""
        url = reverse(
            "admin:notifications_notification_change", args=[obj.notification.pk]
        )
        return format_html('<a href="{}">{}</a>', url, obj.notification.recipient_id)

    notification_link.short_description = "Notification"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
