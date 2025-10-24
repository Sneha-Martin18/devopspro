import logging

import requests
from django.conf import settings
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


class APIGatewayBackend(BaseBackend):
    """
    Custom authentication backend that authenticates users via the API Gateway
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate user via API Gateway
        """
        if not username or not password:
            return None

        try:
            # Authenticate with API Gateway
            auth_url = f"{settings.API_GATEWAY_URL}/api/v1/auth/login/"
            auth_data = {"email": username, "password": password}

            response = requests.post(auth_url, json=auth_data, timeout=10)

            if response.status_code == 200:
                user_data = response.json()

                # Create or get Django user for session management
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        "email": username,
                        "first_name": user_data.get("first_name", ""),
                        "last_name": user_data.get("last_name", ""),
                        "is_active": True,
                    },
                )

                # Store API token and user info in session
                if hasattr(request, "session"):
                    request.session["api_token"] = user_data.get("token")
                    request.session["user_type"] = user_data.get("user_type")
                    request.session["user_id"] = user_data.get("id")
                    request.session["user_data"] = user_data

                logger.info(
                    f"User {username} authenticated successfully via API Gateway"
                )
                return user
            else:
                logger.warning(
                    f"Authentication failed for {username}: {response.status_code}"
                )
                return None

        except requests.RequestException as e:
            logger.error(f"API Gateway authentication error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected authentication error: {e}")
            return None

    def get_user(self, user_id):
        """
        Get user by ID
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
