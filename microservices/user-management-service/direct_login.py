#!/usr/bin/env python3
"""
Direct login script that bypasses Django's problematic middleware
"""
import json
import os
import sys

import django
from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "user_service.settings")
django.setup()


def direct_authenticate(username, password):
    """Direct authentication function"""
    try:
        # Authenticate user
        user = authenticate(username=username, password=password)

        if user is None:
            return {"error": "Invalid credentials", "status": 401}

        if not user.is_active:
            return {"error": "Account is disabled", "status": 401}

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token

        # Update last login
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        # Return success response
        return {
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
            "status": 200,
        }

    except Exception as e:
        return {"error": f"Internal server error: {str(e)}", "status": 500}


if __name__ == "__main__":
    # Test the authentication
    result = direct_authenticate("admin@gmail.com", "admin")
    print(json.dumps(result, indent=2))
