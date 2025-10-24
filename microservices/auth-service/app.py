#!/usr/bin/env python3
"""
Standalone Authentication Service
"""
import json
import logging
import os
import subprocess

from flask import Flask, jsonify, request

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route("/api/v1/users/login/", methods=["POST"])
def login():
    """Login endpoint that directly authenticates with Django"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON data"}), 400

        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return jsonify({"error": "Username and password required"}), 400

        # Escape single quotes in username and password
        username = username.replace("'", "\\'")
        password = password.replace("'", "\\'")

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
        print('AUTH_SUCCESS:' + json.dumps(result))
    else:
        print('AUTH_ERROR:' + json.dumps({{'error': 'Invalid credentials'}}))
except Exception as e:
    print('AUTH_ERROR:' + json.dumps({{'error': str(e)}}))
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

        if result.returncode == 0:
            # Parse output looking for our markers
            output_lines = result.stdout.split("\n")
            for line in output_lines:
                if line.startswith("AUTH_SUCCESS:"):
                    auth_result = json.loads(line[13:])  # Remove 'AUTH_SUCCESS:' prefix
                    return jsonify(auth_result), 200
                elif line.startswith("AUTH_ERROR:"):
                    auth_result = json.loads(line[11:])  # Remove 'AUTH_ERROR:' prefix
                    return jsonify(auth_result), 401

            # Fallback: look for JSON in any line
            for line in output_lines:
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    try:
                        auth_result = json.loads(line)
                        if "access_token" in auth_result:
                            return jsonify(auth_result), 200
                        else:
                            return jsonify(auth_result), 401
                    except json.JSONDecodeError:
                        continue

            logger.error(f"No valid JSON found in output: {result.stdout}")
            return (
                jsonify({"error": "Authentication service error - no valid response"}),
                500,
            )
        else:
            logger.error(f"Auth command failed: {result.stderr}")
            return jsonify({"error": "Authentication service error"}), 500

    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        return jsonify({"error": "Internal authentication error"}), 500


@app.route("/health/", methods=["GET"])
def health():
    """Health check endpoint"""
    return (
        jsonify(
            {
                "status": "healthy",
                "service": "auth-service",
                "message": "Authentication service is running",
            }
        ),
        200,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8010, debug=True)
