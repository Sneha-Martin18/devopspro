import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .models import CustomUser

logger = logging.getLogger(__name__)


@shared_task
def send_welcome_email(user_id):
    """Send welcome email to new user"""
    try:
        user = CustomUser.objects.get(id=user_id)

        subject = "Welcome to Student Management System"
        message = f"Hello {user.get_full_name()},\n\nWelcome to our Student Management System!"

        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False,
        )

        logger.info(f"Welcome email sent to user {user.username}")
        return f"Welcome email sent to {user.email}"

    except CustomUser.DoesNotExist:
        logger.error(f"User with id {user_id} not found")
        return f"User with id {user_id} not found"
    except Exception as e:
        logger.error(f"Failed to send welcome email: {str(e)}")
        return f"Failed to send welcome email: {str(e)}"


@shared_task
def send_password_reset_email(user_id, reset_token):
    """Send password reset email"""
    try:
        user = CustomUser.objects.get(id=user_id)

        subject = "Password Reset Request"
        message = f"Hello {user.get_full_name()},\n\nYou requested a password reset. Use this token: {reset_token}"

        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False,
        )

        logger.info(f"Password reset email sent to user {user.username}")
        return f"Password reset email sent to {user.email}"

    except CustomUser.DoesNotExist:
        logger.error(f"User with id {user_id} not found")
        return f"User with id {user_id} not found"
    except Exception as e:
        logger.error(f"Failed to send password reset email: {str(e)}")
        return f"Failed to send password reset email: {str(e)}"


@shared_task
def cleanup_expired_sessions():
    """Session cleanup disabled - no session tracking"""
    logger.info("Session cleanup skipped - session tracking disabled")
    return "Session cleanup skipped - session tracking disabled"
