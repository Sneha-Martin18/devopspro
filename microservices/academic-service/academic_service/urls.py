"""
URL configuration for academic_service project.
"""
from datetime import datetime

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def health_check(request):
    """Health check endpoint"""
    return JsonResponse(
        {
            "status": "healthy",
            "service": "academic-service",
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/academics/", include("academics.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("health/", health_check, name="health-check"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
