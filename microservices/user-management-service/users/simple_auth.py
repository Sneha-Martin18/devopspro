import json
import logging

from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def simple_login(request):
    """Simple login endpoint that returns JSON only"""
    try:
        # Parse JSON data
        data = json.loads(request.body)
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return JsonResponse({"error": "Username and password required"}, status=400)

        # Authenticate user
        user = authenticate(username=username, password=password)

        if user is None:
            return JsonResponse({"error": "Invalid credentials"}, status=401)

        if not user.is_active:
            return JsonResponse({"error": "Account is disabled"}, status=401)

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token

        # Update last login
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        # Return success response
        return JsonResponse(
            {
                "access_token": str(access_token),
                "refresh_token": str(refresh),
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "user_type": user.user_type,
                    "is_active": user.is_active,
                    "date_joined": user.date_joined.isoformat(),
                },
                "message": "Login successful",
            },
            status=200,
        )

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON data"}, status=400)
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return JsonResponse({"error": "Internal server error"}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def simple_health(request):
    """Simple health check endpoint"""
    return JsonResponse(
        {
            "status": "healthy",
            "service": "user-management",
            "timestamp": timezone.now().isoformat(),
        },
        status=200,
    )
