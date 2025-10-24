"""
URL configuration for notifications app.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(
    r"templates", views.NotificationTemplateViewSet, basename="notification-template"
)
router.register(r"notifications", views.NotificationViewSet, basename="notification")
router.register(
    r"preferences",
    views.NotificationPreferenceViewSet,
    basename="notification-preference",
)
router.register(r"logs", views.NotificationLogViewSet, basename="notification-log")

# The API URLs are now determined automatically by the router.
urlpatterns = [
    path("", include(router.urls)),
]
