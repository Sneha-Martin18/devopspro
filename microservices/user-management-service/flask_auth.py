#!/usr/bin/env python3
"""
Flask-based authentication service that uses Django models
"""
import json
import os
import sys

import django
from flask import Flask, jsonify, request

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "user_service.settings")
django.setup()

from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

app = Flask(__name__)


@app.route("/api/v1/users/login/", methods=["POST"])
def login():
    """Flask-based login endpoint"""
    try:
        # Parse JSON data
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON data"}), 400

        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return jsonify({"error": "Username and password required"}), 400

        # Authenticate user using Django
        user = authenticate(username=username, password=password)

        if user is None:
            return jsonify({"error": "Invalid credentials"}), 401

        if not user.is_active:
            return jsonify({"error": "Account is disabled"}), 401

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token

        # Update last login
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        # Return success response
        return (
            jsonify(
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
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@app.route("/api/v1/users/health/", methods=["GET"])
def health():
    """Health check endpoint"""
    return (
        jsonify(
            {
                "status": "healthy",
                "service": "user-management-flask",
                "timestamp": timezone.now().isoformat(),
            }
        ),
        200,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001, debug=False)
