#!/usr/bin/env python3
"""
Direct authentication handler for API Gateway
"""
import json
import logging
import subprocess

logger = logging.getLogger(__name__)


def authenticate_user(username, password):
    """
    Authenticate user directly using Django shell in user-management container
    """
    try:
        auth_command = f"""
import os
import django
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
import json

try:
    user = authenticate(username='{username}', password='{password}')
    if user and user.is_active:
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        
        result = {{
            'access_token': str(access_token),
            'refresh_token': str(refresh),
            'user': {{
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'user_type': user.user_type,
                'is_active': user.is_active,
            }},
            'message': 'Login successful'
        }}
        print(json.dumps(result))
    else:
        print(json.dumps({{'error': 'Invalid credentials'}}))
except Exception as e:
    print(json.dumps({{'error': str(e)}}))
"""

        # Execute authentication via docker compose exec
        result = subprocess.run(
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "user-management",
                "python",
                "manage.py",
                "shell",
                "-c",
                auth_command,
            ],
            capture_output=True,
            text=True,
            cwd="/app",
        )

        if result.returncode == 0 and result.stdout.strip():
            # Parse the JSON output
            output_lines = result.stdout.strip().split("\n")
            json_line = None
            for line in output_lines:
                if line.strip().startswith("{"):
                    json_line = line.strip()
                    break

            if json_line:
                auth_result = json.loads(json_line)
                return auth_result, 200 if "access_token" in auth_result else 401
            else:
                return {"error": "No valid JSON response from authentication"}, 500
        else:
            logger.error(f"Auth command failed: {result.stderr}")
            return {"error": "Authentication service error"}, 500

    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        return {"error": "Internal authentication error"}, 500
