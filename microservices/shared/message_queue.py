import json
import logging
from typing import Any, Callable, Dict

from celery import Celery
from django.conf import settings

logger = logging.getLogger(__name__)


class MessageQueue:
    """Message queue for inter-service communication"""

    def __init__(self):
        self.celery_app = Celery("microservices")
        self.celery_app.config_from_object("django.conf:settings", namespace="CELERY")

    def publish_event(
        self, event_type: str, data: Dict[str, Any], routing_key: str = None
    ):
        """Publish an event to the message queue"""
        try:
            message = {
                "event_type": event_type,
                "data": data,
                "timestamp": str(timezone.now()),
            }

            # Use Celery to send the message
            self.celery_app.send_task(
                "process_event", args=[message], routing_key=routing_key or event_type
            )

            logger.info(f"Published event: {event_type}")

        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {str(e)}")

    def subscribe_to_events(self, event_types: list, callback: Callable):
        """Subscribe to specific event types"""
        # This would be implemented with a proper message broker like RabbitMQ
        # For now, we'll use Celery tasks
        pass


# Event types
class EventTypes:
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    STUDENT_ENROLLED = "student.enrolled"
    STAFF_ASSIGNED = "staff.assigned"


# Message queue instance
message_queue = MessageQueue()


def publish_user_created_event(user_id: int, user_type: str, user_data: Dict[str, Any]):
    """Publish user created event"""
    event_data = {"user_id": user_id, "user_type": user_type, "user_data": user_data}
    message_queue.publish_event(EventTypes.USER_CREATED, event_data)


def publish_user_updated_event(user_id: int, updated_fields: Dict[str, Any]):
    """Publish user updated event"""
    event_data = {"user_id": user_id, "updated_fields": updated_fields}
    message_queue.publish_event(EventTypes.USER_UPDATED, event_data)


def publish_student_enrolled_event(student_id: int, course_id: str):
    """Publish student enrollment event"""
    event_data = {"student_id": student_id, "course_id": course_id}
    message_queue.publish_event(EventTypes.STUDENT_ENROLLED, event_data)
