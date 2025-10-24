from django.urls import path

from . import views

urlpatterns = [
    # Health check
    path("health/", views.health_check, name="attendance-health-check"),
    # Attendance Sessions
    path(
        "sessions/",
        views.AttendanceSessionListCreateView.as_view(),
        name="session-list-create",
    ),
    path(
        "sessions/<int:pk>/",
        views.AttendanceSessionDetailView.as_view(),
        name="session-detail",
    ),
    # Attendance Records
    path(
        "records/",
        views.AttendanceListCreateView.as_view(),
        name="attendance-list-create",
    ),
    path(
        "records/<int:pk>/",
        views.AttendanceDetailView.as_view(),
        name="attendance-detail",
    ),
    # Student specific attendance
    path(
        "students/<int:student_id>/",
        views.StudentAttendanceView.as_view(),
        name="student-attendance",
    ),
    # Session specific attendance
    path(
        "sessions/<int:session_id>/attendance/",
        views.SessionAttendanceView.as_view(),
        name="session-attendance",
    ),
    # Bulk attendance marking
    path("bulk-mark/", views.bulk_attendance_mark, name="bulk-attendance-mark"),
    # Attendance statistics
    path("stats/", views.attendance_stats, name="attendance-stats"),
    # Attendance Reports
    path(
        "reports/",
        views.AttendanceReportListCreateView.as_view(),
        name="report-list-create",
    ),
    path(
        "reports/<int:pk>/",
        views.AttendanceReportDetailView.as_view(),
        name="report-detail",
    ),
    # Attendance Settings
    path(
        "settings/",
        views.AttendanceSettingsListCreateView.as_view(),
        name="settings-list-create",
    ),
    path(
        "settings/<int:pk>/",
        views.AttendanceSettingsDetailView.as_view(),
        name="settings-detail",
    ),
]
