import logging

import requests
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

logger = logging.getLogger(__name__)


class APIClient:
    """
    Client for communicating with microservices through API Gateway
    """

    def __init__(self, request=None):
        self.request = request
        self.base_url = settings.API_GATEWAY_URL
        self.headers = {"Content-Type": "application/json"}

        # Add authentication token if available
        if request and hasattr(request, "session"):
            token = request.session.get("api_token")
            if token:
                self.headers["Authorization"] = f"Bearer {token}"

    def get(self, endpoint, params=None):
        """Make GET request to API Gateway"""
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.get(
                url, headers=self.headers, params=params, timeout=30
            )
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"GET request failed for {endpoint}: {e}")
            return None

    def post(self, endpoint, data=None):
        """Make POST request to API Gateway"""
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.post(url, headers=self.headers, json=data, timeout=30)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"POST request failed for {endpoint}: {e}")
            return None

    def put(self, endpoint, data=None):
        """Make PUT request to API Gateway"""
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.put(url, headers=self.headers, json=data, timeout=30)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"PUT request failed for {endpoint}: {e}")
            return None

    def delete(self, endpoint):
        """Make DELETE request to API Gateway"""
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.delete(url, headers=self.headers, timeout=30)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"DELETE request failed for {endpoint}: {e}")
            return None

    def _handle_response(self, response):
        """Handle API response"""
        if response.status_code in [200, 201]:
            try:
                return response.json()
            except ValueError:
                return {"success": True}
        elif response.status_code == 204:
            return {"success": True}
        elif response.status_code in [401, 403]:
            logger.warning(f"Authentication error: {response.status_code}")
            if self.request:
                messages.error(
                    self.request, "Authentication required. Please login again."
                )
            return None
        else:
            logger.error(f"API error: {response.status_code} - {response.text}")
            if self.request:
                try:
                    error_data = response.json()
                    error_msg = error_data.get(
                        "detail", f"API Error: {response.status_code}"
                    )
                except ValueError:
                    error_msg = f"API Error: {response.status_code}"
                messages.error(self.request, error_msg)
            return None


def get_user_type(request):
    """Get user type from session"""
    return str(request.session.get("user_type", "0"))


def get_user_data(request):
    """Get user data from session"""
    return request.session.get("user_data", {})


def is_authenticated(request):
    """Check if user is authenticated"""
    return bool(request.session.get("is_authenticated"))


def require_auth(view_func):
    """Decorator to require authentication"""

    def wrapper(request, *args, **kwargs):
        if not is_authenticated(request):
            messages.error(request, "Please login to access this page.")
            return redirect("login")
        return view_func(request, *args, **kwargs)

    return wrapper


def require_user_type(user_types):
    """Decorator to require specific user types"""

    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not is_authenticated(request):
                messages.error(request, "Please login to access this page.")
                return redirect("login")

            user_type = get_user_type(request)
            if user_type not in user_types:
                messages.error(
                    request, "You don't have permission to access this page."
                )
                return redirect("login")

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
