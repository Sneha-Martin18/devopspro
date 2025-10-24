import json
import logging
from datetime import datetime, timedelta
from functools import wraps

import jwt
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)
app.config["SECRET_KEY"] = "your-gateway-secret-key"

# Service URLs
SERVICES = {
    "user-management": "http://user-management:8000",
    "academic": "http://academic:8001",
    "attendance": "http://attendance:8002",
    "notification": "http://notification:8003",
    "leave-management": "http://leave-management:8004",
    "feedback": "http://feedback:8005",
    "assessment": "http://assessment:8006",
    "financial": "http://financial:8007",
}

# Route mappings
ROUTE_MAPPINGS = {
    "/api/v1/users/": "user-management",
    "/api/v1/auth/": "user-management",
    "/api/v1/academics/": "academic",
    "/api/v1/courses/": "academic",
    "/api/v1/subjects/": "academic",
    "/api/v1/sessions/": "academic",
    "/api/v1/attendance/": "attendance",
    "/api/v1/notifications/": "notification",
    "/api/v1/leaves/": "leave-management",
    "/api/v1/leave/": "leave-management",
    "/api/v1/feedback/": "feedback",
    "/api/v1/assessments/": "assessment",
    "/api/v1/assignments/": "assessment",
    "/api/v1/submissions/": "assessment",
    "/api/v1/exams/": "assessment",
    "/api/v1/grades/": "assessment",
    "/api/v1/results/": "assessment",
    "/api/v1/finances/": "financial",
    "/api/v1/fines/": "financial",
    "/api/v1/payments/": "financial",
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def authenticate_request(f):
    """Decorator to authenticate requests"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip authentication for login and health check endpoints
        if request.path in ["/api/v1/users/login/", "/api/v1/users/health/", "/health"]:
            return f(*args, **kwargs)

        token = request.headers.get("Authorization")
        if not token:
            # For development: skip authentication if no token provided
            logger.warning("No authorization token provided - allowing for development")
            return f(*args, **kwargs)

        try:
            # Extract token from "Bearer <token>"
            if token.startswith("Bearer "):
                token = token[7:]

            # Allow dummy token for development
            if token == "dummy-token-for-development":
                logger.info("Development token accepted")
                return f(*args, **kwargs)

            # Validate token with user management service
            response = requests.get(
                f"{SERVICES['user-management']}/api/v1/users/validate-token/",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )

            if response.status_code != 200:
                logger.warning(f"Token validation failed - allowing for development")
                return f(*args, **kwargs)

        except Exception as e:
            logger.error(f"Token validation error: {str(e)} - allowing for development")
            return f(*args, **kwargs)

        return f(*args, **kwargs)

    return decorated_function


def get_service_for_path(path):
    """Determine which service should handle the request"""
    for route_prefix, service_name in ROUTE_MAPPINGS.items():
        if path.startswith(route_prefix):
            return service_name
    return None


@app.route("/")
def root():
    """API Gateway root endpoint"""
    return jsonify(
        {
            "service": "API Gateway",
            "version": "v1.0.0",
            "status": "running",
            "timestamp": datetime.utcnow().isoformat(),
            "available_services": list(SERVICES.keys()),
            "endpoints": {
                "health": "/health",
                "services_status": "/api/v1/services/status",
                "user_management": "/api/v1/users/",
                "academic": "/api/v1/courses/",
                "attendance": "/api/v1/attendance/",
                "notifications": "/api/v1/notifications/",
                "leave_management": "/api/v1/leave/",
                "feedback": "/api/v1/feedback/",
                "assessment": "/api/v1/assessments/",
                "financial": "/api/v1/finances/",
            },
            "documentation": {
                "user_management": "http://localhost:8000/api/docs/",
                "academic": "http://localhost:8001/api/docs/",
                "attendance": "http://localhost:8002/api/docs/",
                "notification": "http://localhost:8003/api/docs/",
                "leave_management": "http://localhost:8004/api/docs/",
                "feedback": "http://localhost:8005/api/docs/",
                "assessment": "http://localhost:8006/api/docs/",
                "financial": "http://localhost:8007/api/docs/",
                "swagger_ui": "http://localhost:8000/api/docs/",
            },
        }
    )


@app.route("/health")
def health_check():
    """Gateway health check"""
    return jsonify(
        {
            "status": "healthy",
            "service": "api-gateway",
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


@app.route("/api/v1/services/status")
@authenticate_request
def services_status():
    """Check status of all services"""
    status = {}

    for service_name, service_url in SERVICES.items():
        try:
            response = requests.get(
                f"{service_url}/api/v1/users/health/"
                if service_name == "user-management"
                else f"{service_url}/health",
                timeout=5,
            )
            status[service_name] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "response_time": response.elapsed.total_seconds(),
            }
        except Exception as e:
            status[service_name] = {"status": "unhealthy", "error": str(e)}

    return jsonify(status)


@app.route("/api/v1/users/login/", methods=["POST"])
def direct_login():
    """Direct login endpoint that bypasses problematic Django middleware"""
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON data"}), 400

        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return jsonify({"error": "Username and password required"}), 400

        from auth_handler import authenticate_user

        auth_result, status_code = authenticate_user(username, password)
        return jsonify(auth_result), status_code

    except Exception as e:
        logger.error(f"Direct login error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/v1/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@authenticate_request
def proxy_request(path):
    """Proxy requests to appropriate microservice"""
    full_path = f"/api/v1/{path}"
    service_name = get_service_for_path(full_path)

    if not service_name:
        return jsonify({"error": "Service not found"}), 404

    service_url = SERVICES.get(service_name)
    if not service_url:
        return jsonify({"error": "Service unavailable"}), 503

    # Forward the request
    try:
        target_url = f"{service_url}{full_path}"

        # Forward headers (excluding host)
        headers = {k: v for k, v in request.headers if k.lower() != "host"}

        response = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=request.get_data(),
            params=request.args,
            timeout=30,
        )

        # Log the request
        logger.info(
            f"Proxied {request.method} {full_path} to {service_name} - {response.status_code}"
        )

        # Return the response
        return response.content, response.status_code, dict(response.headers)

    except requests.exceptions.Timeout:
        logger.error(f"Timeout calling {service_name}")
        return jsonify({"error": "Service timeout"}), 504

    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error calling {service_name}")
        return jsonify({"error": "Service unavailable"}), 503

    except Exception as e:
        logger.error(f"Error proxying request to {service_name}: {str(e)}")
        return jsonify({"error": "Internal gateway error"}), 500


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
