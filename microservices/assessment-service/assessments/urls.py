from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (AssignmentViewSet, ExamViewSet, GradeScaleViewSet,
                    GradeViewSet, StudentResultViewSet, SubmissionViewSet)

router = DefaultRouter()
router.register(r"assignments", AssignmentViewSet)
router.register(r"submissions", SubmissionViewSet)
router.register(r"exams", ExamViewSet)
router.register(r"grades", GradeViewSet)
router.register(r"grade-scales", GradeScaleViewSet)
router.register(r"results", StudentResultViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
