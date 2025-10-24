from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import simple_auth, views

urlpatterns = [
    # Authentication endpoints
    path("register/", views.UserRegistrationView.as_view(), name="user-register"),
    path("login/", simple_auth.simple_login, name="simple-login"),
    path("login-old/", views.UserLoginView.as_view(), name="user-login"),
    path("logout/", views.UserLogoutView.as_view(), name="user-logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    # User profile endpoints
    path("profile/", views.UserProfileView.as_view(), name="user-profile"),
    path(
        "change-password/", views.PasswordChangeView.as_view(), name="change-password"
    ),
    # path('sessions/', views.UserSessionListView.as_view(), name='user-sessions'),  # Disabled
    # Student endpoints
    path(
        "students/", views.StudentListCreateView.as_view(), name="student-list-create"
    ),
    path(
        "students/<int:pk>/", views.StudentDetailView.as_view(), name="student-detail"
    ),
    # Staff endpoints
    path("staff/", views.StaffListCreateView.as_view(), name="staff-list-create"),
    path("staff/<int:pk>/", views.StaffDetailView.as_view(), name="staff-detail"),
    # Admin HOD endpoints
    path("admins/", views.AdminHODListView.as_view(), name="admin-list"),
    # Inter-service communication endpoints
    path("user/<int:user_id>/", views.get_user_by_id, name="get-user-by-id"),
    path("validate-token/", views.validate_token, name="validate-token"),
    # Health check
    path("health/", simple_auth.simple_health, name="simple-health"),
    path("health-old/", views.health_check, name="health-check"),
]
