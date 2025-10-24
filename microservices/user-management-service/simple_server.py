#!/usr/bin/env python3
"""
Simple HTTP server for authentication that bypasses Django middleware
"""
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "user_service.settings")
django.setup()

from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken


class AuthHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/api/v1/users/login/":
            try:
                # Read request body
                content_length = int(self.headers["Content-Length"])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode("utf-8"))

                username = data.get("username")
                password = data.get("password")

                if not username or not password:
                    self.send_error_response(
                        {"error": "Username and password required"}, 400
                    )
                    return

                # Authenticate user
                user = authenticate(username=username, password=password)

                if user is None:
                    self.send_error_response({"error": "Invalid credentials"}, 401)
                    return

                if not user.is_active:
                    self.send_error_response({"error": "Account is disabled"}, 401)
                    return

                # Generate JWT tokens
                refresh = RefreshToken.for_user(user)
                access_token = refresh.access_token

                # Update last login
                user.last_login = timezone.now()
                user.save(update_fields=["last_login"])

                # Send success response
                response = {
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

                self.send_json_response(response, 200)

            except Exception as e:
                self.send_error_response(
                    {"error": f"Internal server error: {str(e)}"}, 500
                )
        else:
            self.send_error_response({"error": "Not found"}, 404)

    def do_GET(self):
        if self.path == "/api/v1/users/health/":
            response = {
                "status": "healthy",
                "service": "user-management-simple",
                "timestamp": timezone.now().isoformat(),
            }
            self.send_json_response(response, 200)
        else:
            self.send_error_response({"error": "Not found"}, 404)

    def send_json_response(self, data, status_code):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def send_error_response(self, data, status_code):
        self.send_json_response(data, status_code)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()


def run_server():
    server = HTTPServer(("0.0.0.0", 8001), AuthHandler)
    print("Simple auth server running on port 8001")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
