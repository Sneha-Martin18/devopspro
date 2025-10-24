from django.urls import path

from . import views

urlpatterns = [
    # Health check
    path("health/", views.health_check, name="academic-health-check"),
    # Session Year endpoints
    path(
        "sessions/",
        views.SessionYearListCreateView.as_view(),
        name="session-list-create",
    ),
    path(
        "session-years/",
        views.SessionYearListCreateView.as_view(),
        name="session-year-list-create",
    ),
    path(
        "sessions/<int:pk>/",
        views.SessionYearDetailView.as_view(),
        name="session-detail",
    ),
    path(
        "session-years/<int:pk>/",
        views.SessionYearDetailView.as_view(),
        name="session-year-detail",
    ),
    path("sessions/active/", views.active_session, name="active-session"),
    # Course endpoints
    path("courses/", views.CourseListCreateView.as_view(), name="course-list-create"),
    path("courses/<int:pk>/", views.CourseDetailView.as_view(), name="course-detail"),
    path(
        "courses/<int:course_id>/subjects/",
        views.course_subjects,
        name="course-subjects",
    ),
    # Subject endpoints
    path(
        "subjects/", views.SubjectListCreateView.as_view(), name="subject-list-create"
    ),
    path(
        "subjects/<int:pk>/", views.SubjectDetailView.as_view(), name="subject-detail"
    ),
    # Enrollment endpoints
    path(
        "enrollments/",
        views.EnrollmentListCreateView.as_view(),
        name="enrollment-list-create",
    ),
    path(
        "enrollments/<int:pk>/",
        views.EnrollmentDetailView.as_view(),
        name="enrollment-detail",
    ),
    path(
        "enrollments/student/<int:student_id>/",
        views.student_enrollments,
        name="student-enrollments",
    ),
    path("enrollments/enroll/", views.enroll_student, name="enroll-student"),
    # Subject Enrollment endpoints
    path(
        "subject-enrollments/",
        views.SubjectEnrollmentListCreateView.as_view(),
        name="subject-enrollment-list-create",
    ),
    path(
        "subject-enrollments/<int:pk>/",
        views.SubjectEnrollmentDetailView.as_view(),
        name="subject-enrollment-detail",
    ),
    path("subject-enrollments/enroll/", views.enroll_subject, name="enroll-subject"),
]
