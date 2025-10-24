import logging
from typing import Any, Dict, Optional

import requests
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger(__name__)


class ServiceClient:
    """Base class for inter-service communication"""

    def __init__(self, base_url: str, service_name: str):
        self.base_url = base_url.rstrip("/")
        self.service_name = service_name
        self.timeout = 30

    def _get_headers(self, token: Optional[str] = None) -> Dict[str, str]:
        """Get headers for API requests"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": f"user-management-service/1.0",
        }

        if token:
            headers["Authorization"] = f"Bearer {token}"

        return headers

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Make HTTP request to another service"""
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers(token)

        try:
            response = requests.request(
                method=method, url=url, json=data, headers=headers, timeout=self.timeout
            )

            if response.status_code >= 400:
                logger.error(
                    f"Service {self.service_name} error: {response.status_code} - {response.text}"
                )
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "message": response.text,
                }

            return {
                "success": True,
                "data": response.json() if response.content else None,
                "status_code": response.status_code,
            }

        except requests.exceptions.Timeout:
            logger.error(f"Timeout calling {self.service_name} service")
            return {"success": False, "error": "timeout"}

        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error calling {self.service_name} service")
            return {"success": False, "error": "connection_error"}

        except Exception as e:
            logger.error(f"Unexpected error calling {self.service_name}: {str(e)}")
            return {"success": False, "error": "unexpected_error", "message": str(e)}


class AcademicServiceClient(ServiceClient):
    """Client for Academic Service communication"""

    def __init__(self):
        base_url = getattr(settings, "ACADEMIC_SERVICE_URL", "http://localhost:8001")
        super().__init__(base_url, "academic-service")

    def get_course(self, course_id: str, token: str) -> Dict[str, Any]:
        """Get course information"""
        return self._make_request("GET", f"/api/v1/courses/{course_id}/", token=token)

    def get_session_year(self, session_id: str, token: str) -> Dict[str, Any]:
        """Get session year information"""
        return self._make_request("GET", f"/api/v1/sessions/{session_id}/", token=token)

    def validate_course_enrollment(
        self, student_id: int, course_id: str, token: str
    ) -> Dict[str, Any]:
        """Validate if student can enroll in course"""
        data = {"student_id": student_id, "course_id": course_id}
        return self._make_request(
            "POST", "/api/v1/enrollments/validate/", data=data, token=token
        )


class NotificationServiceClient(ServiceClient):
    """Client for Notification Service communication"""

    def __init__(self):
        base_url = getattr(
            settings, "NOTIFICATION_SERVICE_URL", "http://localhost:8002"
        )
        super().__init__(base_url, "notification-service")

    def send_notification(
        self,
        user_id: int,
        message: str,
        notification_type: str = "info",
        token: str = None,
    ) -> Dict[str, Any]:
        """Send notification to user"""
        data = {"user_id": user_id, "message": message, "type": notification_type}
        return self._make_request(
            "POST", "/api/v1/notifications/", data=data, token=token
        )

    def send_bulk_notification(
        self,
        user_ids: list,
        message: str,
        notification_type: str = "info",
        token: str = None,
    ) -> Dict[str, Any]:
        """Send notification to multiple users"""
        data = {"user_ids": user_ids, "message": message, "type": notification_type}
        return self._make_request(
            "POST", "/api/v1/notifications/bulk/", data=data, token=token
        )


class AttendanceServiceClient(ServiceClient):
    """Client for Attendance Service communication"""

    def __init__(self):
        base_url = getattr(settings, "ATTENDANCE_SERVICE_URL", "http://localhost:8003")
        super().__init__(base_url, "attendance-service")

    def get_student_attendance(self, student_id: int, token: str) -> Dict[str, Any]:
        """Get student attendance summary"""
        return self._make_request(
            "GET", f"/api/v1/attendance/student/{student_id}/", token=token
        )

    def mark_attendance(
        self, student_id: int, subject_id: str, status: bool, token: str
    ) -> Dict[str, Any]:
        """Mark student attendance"""
        data = {"student_id": student_id, "subject_id": subject_id, "status": status}
        return self._make_request("POST", "/api/v1/attendance/", data=data, token=token)


# Service client instances
academic_client = AcademicServiceClient()
notification_client = NotificationServiceClient()
attendance_client = AttendanceServiceClient()


def get_service_token() -> str:
    """Generate service-to-service authentication token"""
    # In production, use a service account or API key
    # For now, we'll use a system user token
    try:
        from .models import CustomUser

        system_user = CustomUser.objects.filter(username="system").first()
        if system_user:
            refresh = RefreshToken.for_user(system_user)
            return str(refresh.access_token)
    except Exception as e:
        logger.error(f"Failed to generate service token: {str(e)}")

    return ""


def notify_user_created(user_id: int, user_type: str):
    """Notify other services when a user is created"""
    token = get_service_token()

    # Notify notification service
    message = f"New {user_type.lower()} account created"
    notification_client.send_notification(user_id, message, "info", token)

    logger.info(f"Notified services about new user creation: {user_id}")


def validate_student_course_access(student_id: int, course_id: str) -> bool:
    """Validate if student has access to a course"""
    token = get_service_token()
    result = academic_client.validate_course_enrollment(student_id, course_id, token)

    return result.get("success", False) and result.get("data", {}).get("valid", False)
