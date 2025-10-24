"""
Custom middleware for authentication and session handling
"""
import logging

from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.cache import add_never_cache_headers

logger = logging.getLogger(__name__)


class AuthenticationMiddleware:
    """
    Middleware to handle authentication, session validation, and CSRF protection
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.login_url = reverse("login")
        self.public_paths = [
            self.login_url,
            reverse("health_check"),
            "/favicon.ico",
        ]

        # API endpoints that don't require CSRF
        self.csrf_exempt_paths = [
            "/api/",
        ]

    def is_public_path(self, path):
        """Check if path is public"""
        return any(
            path.startswith(p)
            for p in [
                settings.STATIC_URL,
                settings.MEDIA_URL,
                *[str(p) for p in self.public_paths],
            ]
        )

    def is_csrf_exempt(self, path):
        """Check if path is CSRF exempt"""
        return any(path.startswith(p) for p in self.csrf_exempt_paths)

    def __call__(self, request):
        # Skip middleware for public paths
        if self.is_public_path(request.path):
            return self.get_response(request)

        # Skip CSRF check for exempt paths
        if not self.is_csrf_exempt(request.path):
            # Ensure CSRF cookie is set for all responses
            if not request.COOKIES.get(settings.CSRF_COOKIE_NAME):
                from django.middleware.csrf import get_token

                get_token(request)
                logger.debug("CSRF cookie set")

        # Check if user is authenticated
        is_authenticated = bool(request.session.get("is_authenticated", False))

        # Handle unauthenticated users
        if not is_authenticated:
            if request.path != self.login_url:
                # Store the current path for redirect after login
                request.session["next"] = request.get_full_path()
                return redirect(f"{self.login_url}")
            return self.get_response(request)

        # Handle authenticated users trying to access login page
        if is_authenticated and request.path == self.login_url:
            user_type = str(request.session.get("user_type", "0"))
            if user_type == "1":  # HOD/Admin
                return redirect("admin_home")
            elif user_type == "2":  # Staff
                return redirect("staff_home")
            elif user_type == "3":  # Student
                return redirect("student_home")

        # Add cache control headers
        response = self.get_response(request)
        if not self.is_public_path(request.path):
            add_never_cache_headers(response)

        return response
