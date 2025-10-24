import logging
from datetime import datetime, timedelta

import requests
from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_leave_notification(self, leave_request_id, action, recipient_email):
    """Send leave notification via notification service"""
    try:
        from .models import LeaveRequest

        leave_request = LeaveRequest.objects.get(id=leave_request_id)

        # Prepare notification data
        notification_data = {
            "recipient_email": recipient_email,
            "template_code": f"LEAVE_{action}",
            "context": {
                "user_name": leave_request.user_name,
                "leave_type": leave_request.leave_type.name,
                "start_date": leave_request.start_date.strftime("%Y-%m-%d"),
                "end_date": leave_request.end_date.strftime("%Y-%m-%d"),
                "total_days": leave_request.total_days,
                "reason": leave_request.reason,
                "status": leave_request.get_status_display(),
                "request_id": str(leave_request.id),
            },
            "channels": ["email", "in_app"],
            "priority": "high" if action in ["APPROVED", "REJECTED"] else "medium",
        }

        # Send to notification service
        response = requests.post(
            f"{settings.NOTIFICATION_SERVICE_URL}/api/v1/notifications/notifications/",
            json=notification_data,
            timeout=30,
        )

        if response.status_code == 201:
            logger.info(
                f"Leave notification sent successfully for request {leave_request_id}"
            )
        else:
            logger.error(f"Failed to send leave notification: {response.text}")
            raise Exception(f"Notification service returned {response.status_code}")

    except Exception as exc:
        logger.error(f"Error sending leave notification: {str(exc)}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2**self.request.retries), exc=exc)
        raise


@shared_task
def process_leave_approval(leave_request_id, action):
    """Process leave approval/rejection and update balances"""
    try:
        from .models import LeaveBalance, LeaveRequest

        leave_request = LeaveRequest.objects.get(id=leave_request_id)

        # Update leave balance
        if action == "APPROVED":
            balance, created = LeaveBalance.objects.get_or_create(
                user_id=leave_request.user_id,
                leave_type=leave_request.leave_type,
                year=leave_request.start_date.year,
                defaults={
                    "user_type": leave_request.user_type,
                    "total_allocated": leave_request.leave_type.max_days_per_year,
                },
            )

            # Update used days
            balance.used_days += leave_request.total_days
            balance.save()

        elif action == "CANCELLED" and leave_request.status == "CANCELLED":
            # Restore balance if leave was cancelled
            try:
                balance = LeaveBalance.objects.get(
                    user_id=leave_request.user_id,
                    leave_type=leave_request.leave_type,
                    year=leave_request.start_date.year,
                )
                balance.used_days = max(0, balance.used_days - leave_request.total_days)
                balance.save()
            except LeaveBalance.DoesNotExist:
                pass

        logger.info(f"Leave balance updated for request {leave_request_id}")

    except Exception as exc:
        logger.error(f"Error processing leave approval: {str(exc)}")
        raise


@shared_task
def send_leave_reminders():
    """Send reminders for upcoming leaves and pending approvals"""
    try:
        from .models import LeaveRequest

        tomorrow = timezone.now().date() + timedelta(days=1)

        # Remind users about upcoming approved leaves
        upcoming_leaves = LeaveRequest.objects.filter(
            status="APPROVED", start_date=tomorrow
        )

        for leave in upcoming_leaves:
            send_leave_notification.delay(
                leave.id, "REMINDER_UPCOMING", leave.user_email
            )

        # Remind approvers about pending requests older than 2 days
        two_days_ago = timezone.now() - timedelta(days=2)
        pending_requests = LeaveRequest.objects.filter(
            status="PENDING", created_at__lt=two_days_ago
        )

        # Group by approver and send summary
        approver_requests = {}
        for request in pending_requests:
            if request.approver_id:
                if request.approver_id not in approver_requests:
                    approver_requests[request.approver_id] = []
                approver_requests[request.approver_id].append(request)

        for approver_id, requests in approver_requests.items():
            # Send summary notification to approver
            notification_data = {
                "recipient_id": approver_id,
                "template_code": "LEAVE_PENDING_REMINDER",
                "context": {
                    "pending_count": len(requests),
                    "requests": [
                        {
                            "user_name": req.user_name,
                            "leave_type": req.leave_type.name,
                            "start_date": req.start_date.strftime("%Y-%m-%d"),
                            "days_pending": (
                                timezone.now().date() - req.created_at.date()
                            ).days,
                        }
                        for req in requests[:5]  # Limit to 5 in summary
                    ],
                },
                "channels": ["email", "in_app"],
                "priority": "medium",
            }

            requests.post(
                f"{settings.NOTIFICATION_SERVICE_URL}/api/v1/notifications/notifications/",
                json=notification_data,
                timeout=30,
            )

        logger.info(
            f"Sent reminders for {len(upcoming_leaves)} upcoming leaves and {len(pending_requests)} pending approvals"
        )

    except Exception as exc:
        logger.error(f"Error sending leave reminders: {str(exc)}")
        raise


@shared_task
def cleanup_old_leave_data():
    """Clean up old leave data and logs"""
    try:
        from .models import LeaveApproval, LeaveRequest

        # Delete leave requests older than 2 years (except approved ones)
        two_years_ago = timezone.now() - timedelta(days=730)
        old_requests = LeaveRequest.objects.filter(
            created_at__lt=two_years_ago,
            status__in=["REJECTED", "CANCELLED", "WITHDRAWN"],
        )

        deleted_requests = old_requests.count()
        old_requests.delete()

        # Delete approval logs older than 1 year
        one_year_ago = timezone.now() - timedelta(days=365)
        old_approvals = LeaveApproval.objects.filter(action_date__lt=one_year_ago)

        deleted_approvals = old_approvals.count()
        old_approvals.delete()

        logger.info(
            f"Cleaned up {deleted_requests} old leave requests and {deleted_approvals} old approvals"
        )

    except Exception as exc:
        logger.error(f"Error cleaning up old leave data: {str(exc)}")
        raise


@shared_task
def generate_leave_report(user_id, report_type, start_date, end_date):
    """Generate leave reports for users or administrators"""
    try:
        from django.db.models import Count, Sum

        from .models import LeaveBalance, LeaveRequest

        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

        if report_type == "user_summary":
            # Generate user leave summary
            requests = LeaveRequest.objects.filter(
                user_id=user_id, start_date__gte=start_date, end_date__lte=end_date
            )

            summary = {
                "user_id": user_id,
                "period": f"{start_date} to {end_date}",
                "total_requests": requests.count(),
                "approved_requests": requests.filter(status="APPROVED").count(),
                "pending_requests": requests.filter(status="PENDING").count(),
                "rejected_requests": requests.filter(status="REJECTED").count(),
                "total_days_taken": requests.filter(status="APPROVED").aggregate(
                    total=Sum("total_days")
                )["total"]
                or 0,
                "by_leave_type": list(
                    requests.values("leave_type__name")
                    .annotate(count=Count("id"), days=Sum("total_days"))
                    .order_by("-count")
                ),
            }

        elif report_type == "department_summary":
            # Generate department-wide summary
            requests = LeaveRequest.objects.filter(
                start_date__gte=start_date, end_date__lte=end_date
            )

            summary = {
                "period": f"{start_date} to {end_date}",
                "total_requests": requests.count(),
                "by_status": dict(
                    requests.values("status")
                    .annotate(count=Count("id"))
                    .values_list("status", "count")
                ),
                "by_user_type": dict(
                    requests.values("user_type")
                    .annotate(count=Count("id"))
                    .values_list("user_type", "count")
                ),
                "by_leave_type": list(
                    requests.values("leave_type__name")
                    .annotate(count=Count("id"), days=Sum("total_days"))
                    .order_by("-count")
                ),
                "top_users": list(
                    requests.values("user_name")
                    .annotate(count=Count("id"), days=Sum("total_days"))
                    .order_by("-days")[:10]
                ),
            }

        # Store report or send via notification service
        logger.info(
            f"Generated {report_type} report for period {start_date} to {end_date}"
        )
        return summary

    except Exception as exc:
        logger.error(f"Error generating leave report: {str(exc)}")
        raise


@shared_task
def sync_user_data():
    """Sync user data from User Management Service"""
    try:
        from .models import LeaveRequest

        # Get unique user IDs from leave requests
        user_ids = LeaveRequest.objects.values_list("user_id", flat=True).distinct()

        # Fetch user data from User Management Service
        response = requests.post(
            f"{settings.USER_MANAGEMENT_SERVICE_URL}/api/v1/users/bulk_info/",
            json={"user_ids": list(user_ids)},
            timeout=30,
        )

        if response.status_code == 200:
            users_data = response.json()

            # Update leave requests with latest user data
            for user_data in users_data:
                LeaveRequest.objects.filter(user_id=user_data["id"]).update(
                    user_name=f"{user_data['first_name']} {user_data['last_name']}",
                    user_email=user_data["email"],
                )

            logger.info(f"Synced data for {len(users_data)} users")
        else:
            logger.error(f"Failed to sync user data: {response.text}")

    except Exception as exc:
        logger.error(f"Error syncing user data: {str(exc)}")
        raise


@shared_task
def auto_approve_leaves():
    """Auto-approve leaves based on policies"""
    try:
        from .models import LeavePolicy, LeaveRequest

        # Get pending requests that can be auto-approved
        auto_approval_days = getattr(settings, "LEAVE_AUTO_APPROVAL_DAYS", 1)
        cutoff_date = timezone.now() - timedelta(days=auto_approval_days)

        auto_approve_requests = LeaveRequest.objects.filter(
            status="PENDING",
            created_at__lt=cutoff_date,
            leave_type__requires_approval=False,
        )

        approved_count = 0
        for request in auto_approve_requests:
            request.status = "APPROVED"
            request.approver_id = "system"
            request.approver_name = "Auto Approval System"
            request.approved_at = timezone.now()
            request.save()

            # Send notification
            send_leave_notification.delay(request.id, "APPROVED", request.user_email)

            # Process approval
            process_leave_approval.delay(request.id, "APPROVED")

            approved_count += 1

        logger.info(f"Auto-approved {approved_count} leave requests")

    except Exception as exc:
        logger.error(f"Error in auto-approval process: {str(exc)}")
        raise
