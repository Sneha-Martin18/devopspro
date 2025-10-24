"""
API Views for the notifications app.
"""
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (Notification, NotificationLog, NotificationPreference,
                     NotificationStatus, NotificationTemplate)
from .serializers import (BulkCreateNotificationSerializer,
                          CreateNotificationSerializer,
                          NotificationLogSerializer,
                          NotificationPreferenceSerializer,
                          NotificationSerializer,
                          NotificationTemplateSerializer,
                          UpdateNotificationStatusSerializer)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    """API endpoint for notification templates."""

    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["channel", "is_active"]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]


class NotificationViewSet(viewsets.ModelViewSet):
    """API endpoint for notifications."""

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [
        DjangoFilterBackend,
        filters.OrderingFilter,
        filters.SearchFilter,
    ]
    filterset_fields = ["status", "channel", "priority", "recipient_id"]
    search_fields = ["subject", "message"]
    ordering_fields = ["created_at", "scheduled_at", "priority"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "create":
            return CreateNotificationSerializer
        elif self.action == "bulk_create":
            return BulkCreateNotificationSerializer
        elif self.action in ["mark_as_read", "mark_as_unread", "update_status"]:
            return UpdateNotificationStatusSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        queryset = Notification.objects.all()

        # Filter by read/unread status if specified
        is_read = self.request.query_params.get("is_read", None)
        if is_read is not None:
            is_read = is_read.lower() in ("true", "1", "t")
            queryset = queryset.filter(read_at__isnull=not is_read)

        return queryset

    @action(detail=False, methods=["post"])
    def bulk_create(self, request):
        """Create multiple notifications at once."""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            notifications = serializer.save()
            return Response(
                {
                    "message": f"Successfully created {len(notifications)} notifications",
                    "count": len(notifications),
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def mark_as_read(self, request, pk=None):
        """Mark a notification as read."""
        notification = self.get_object()
        notification.mark_as_read()
        return Response(
            {"message": "Notification marked as read", "read_at": notification.read_at}
        )

    @action(detail=True, methods=["post"])
    def mark_as_unread(self, request, pk=None):
        """Mark a notification as unread."""
        notification = self.get_object()
        notification.read_at = None
        notification.save(update_fields=["read_at"])
        return Response({"message": "Notification marked as unread"})

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        """Retry a failed notification."""
        notification = self.get_object()

        if notification.status != NotificationStatus.FAILED:
            return Response(
                {"error": "Only failed notifications can be retried"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if notification.retry_count >= notification.max_retries:
            return Response(
                {"error": "Maximum retry attempts exceeded"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Reset status to pending for retry
        notification.status = NotificationStatus.PENDING
        notification.error_message = ""
        notification.save(update_fields=["status", "error_message"])

        # Import and trigger the task
        from .tasks import send_notification

        send_notification.delay(str(notification.id))

        return Response({"message": "Notification queued for retry"})

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Get notification statistics."""
        queryset = self.get_queryset()

        stats = {
            "total": queryset.count(),
            "pending": queryset.filter(status=NotificationStatus.PENDING).count(),
            "sent": queryset.filter(status=NotificationStatus.SENT).count(),
            "delivered": queryset.filter(status=NotificationStatus.DELIVERED).count(),
            "failed": queryset.filter(status=NotificationStatus.FAILED).count(),
            "by_channel": {
                "email": queryset.filter(channel="email").count(),
                "sms": queryset.filter(channel="sms").count(),
                "in_app": queryset.filter(channel="in_app").count(),
                "push": queryset.filter(channel="push").count(),
            },
            "by_priority": {
                "low": queryset.filter(priority="low").count(),
                "normal": queryset.filter(priority="normal").count(),
                "high": queryset.filter(priority="high").count(),
                "urgent": queryset.filter(priority="urgent").count(),
            },
        }

        return Response(stats)


class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    """API endpoint for notification preferences."""

    queryset = NotificationPreference.objects.all()
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = [
        "user_id",
        "email_enabled",
        "sms_enabled",
        "in_app_enabled",
        "push_enabled",
    ]
    ordering_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]

    @action(detail=False, methods=["get", "post", "put", "patch"])
    def my_preferences(self, request):
        """Get or update current user's notification preferences."""
        user_id = str(request.user.id)

        if request.method == "GET":
            try:
                preferences = NotificationPreference.objects.get(user_id=user_id)
                serializer = self.get_serializer(preferences)
                return Response(serializer.data)
            except NotificationPreference.DoesNotExist:
                return Response(
                    {"message": "No preferences found for current user"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        else:  # POST, PUT, PATCH
            try:
                preferences = NotificationPreference.objects.get(user_id=user_id)
                partial = request.method == "PATCH"
                serializer = self.get_serializer(
                    preferences, data=request.data, partial=partial
                )
            except NotificationPreference.DoesNotExist:
                data = request.data.copy()
                data["user_id"] = user_id
                serializer = self.get_serializer(data=data)

            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NotificationLogViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for notification logs (read-only)."""

    queryset = NotificationLog.objects.all()
    serializer_class = NotificationLogSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["notification", "status"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]
