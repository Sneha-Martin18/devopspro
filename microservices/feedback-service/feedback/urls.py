from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"categories", views.FeedbackCategoryViewSet)
router.register(r"feedback", views.FeedbackViewSet)
router.register(r"responses", views.FeedbackResponseViewSet)
router.register(r"templates", views.FeedbackTemplateViewSet)
router.register(r"surveys", views.FeedbackSurveyViewSet)
router.register(r"analytics", views.FeedbackAnalyticsViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
