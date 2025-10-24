"""
URL configuration for attendance_service project.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def health_check(request):
    """Health check endpoint"""
    return Response(
        {
            "status": "healthy",
            "service": "attendance-service",
            "timestamp": request.META.get("HTTP_DATE", ""),
        }
    )


urlpatterns = [
    path("admin/", admin.site.urls),
    # API endpoints
    path("api/v1/attendance/", include("attendance.urls")),
    # API documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    # Health check
    path("health/", health_check, name="health-check"),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
