"""
URL configuration for notification_service project.
"""
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def health_check(request):
    """Health check endpoint for the notification service."""
    return JsonResponse(
        {"status": "healthy", "service": "notification-service", "version": "1.0.0"}
    )


urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # Health check
    path("health/", health_check, name="health-check"),
    # API Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    # Notifications API
    path("api/v1/notifications/", include("notifications.urls")),
]
