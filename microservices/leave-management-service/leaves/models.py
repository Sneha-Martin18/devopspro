import uuid
from datetime import datetime, timedelta

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class LeaveType(models.Model):
    """Model for different types of leave"""

    LEAVE_CATEGORIES = [
        ("SICK", "Sick Leave"),
        ("CASUAL", "Casual Leave"),
        ("EMERGENCY", "Emergency Leave"),
        ("MATERNITY", "Maternity Leave"),
        ("PATERNITY", "Paternity Leave"),
        ("VACATION", "Vacation Leave"),
        ("STUDY", "Study Leave"),
        ("BEREAVEMENT", "Bereavement Leave"),
        ("MEDICAL", "Medical Leave"),
        ("OTHER", "Other"),
    ]

    USER_TYPES = [
        ("STUDENT", "Student"),
        ("STAFF", "Staff"),
        ("BOTH", "Both"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=20, choices=LEAVE_CATEGORIES)
    description = models.TextField(blank=True)
    applicable_to = models.CharField(max_length=10, choices=USER_TYPES, default="BOTH")
    max_days_per_request = models.PositiveIntegerField(default=30)
    max_days_per_year = models.PositiveIntegerField(default=365)
    requires_approval = models.BooleanField(default=True)
    advance_notice_days = models.PositiveIntegerField(default=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "leave_types"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["category"]),
            models.Index(fields=["applicable_to"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class LeaveRequest(models.Model):
    """Model for leave requests"""

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
        ("WITHDRAWN", "Withdrawn"),
    ]

    PRIORITY_CHOICES = [
        ("LOW", "Low"),
        ("MEDIUM", "Medium"),
        ("HIGH", "High"),
        ("URGENT", "Urgent"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # User information (stored as IDs for microservice architecture)
    user_id = models.CharField(
        max_length=100, help_text="User ID from User Management Service"
    )
    user_type = models.CharField(
        max_length=20, choices=[("STUDENT", "Student"), ("STAFF", "Staff")]
    )
    user_name = models.CharField(
        max_length=200, help_text="Cached user name for display"
    )
    user_email = models.EmailField(help_text="Cached user email for notifications")

    # Leave details
    leave_type = models.ForeignKey(
        LeaveType, on_delete=models.CASCADE, related_name="requests"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    total_days = models.PositiveIntegerField()
    reason = models.TextField()
    emergency_contact = models.CharField(max_length=15, blank=True)
    attachment = models.URLField(blank=True, help_text="URL to uploaded document")

    # Status and approval
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default="MEDIUM"
    )

    # Approval workflow
    approver_id = models.CharField(
        max_length=100, blank=True, help_text="Approver ID from User Management Service"
    )
    approver_name = models.CharField(max_length=200, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    # Academic context (for students)
    academic_year = models.CharField(max_length=20, blank=True)
    semester = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = "leave_requests"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user_id"]),
            models.Index(fields=["status"]),
            models.Index(fields=["start_date"]),
            models.Index(fields=["end_date"]),
            models.Index(fields=["user_type"]),
            models.Index(fields=["approver_id"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.user_name} - {self.leave_type.name} ({self.start_date} to {self.end_date})"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValidationError("Start date cannot be after end date")

            if self.start_date < timezone.now().date():
                raise ValidationError("Cannot request leave for past dates")

            # Calculate total days
            self.total_days = (self.end_date - self.start_date).days + 1

            # Check against leave type limits
            if (
                self.leave_type
                and self.total_days > self.leave_type.max_days_per_request
            ):
                raise ValidationError(
                    f"Leave request exceeds maximum allowed days ({self.leave_type.max_days_per_request}) for {self.leave_type.name}"
                )

            # Check advance notice
            if self.leave_type and self.leave_type.advance_notice_days > 0:
                notice_date = timezone.now().date() + timedelta(
                    days=self.leave_type.advance_notice_days
                )
                if self.start_date < notice_date:
                    raise ValidationError(
                        f"Leave must be requested at least {self.leave_type.advance_notice_days} days in advance"
                    )

    def save(self, *args, **kwargs):
        if self.start_date and self.end_date:
            self.total_days = (self.end_date - self.start_date).days + 1

        if not self.submitted_at and self.status != "PENDING":
            self.submitted_at = timezone.now()

        super().save(*args, **kwargs)

    @property
    def is_current(self):
        """Check if leave is currently active"""
        today = timezone.now().date()
        return self.status == "APPROVED" and self.start_date <= today <= self.end_date

    @property
    def is_upcoming(self):
        """Check if leave is upcoming"""
        today = timezone.now().date()
        return self.status == "APPROVED" and self.start_date > today

    @property
    def days_until_start(self):
        """Days until leave starts"""
        if self.start_date:
            return (self.start_date - timezone.now().date()).days
        return None


class LeaveBalance(models.Model):
    """Model to track leave balance for users"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.CharField(max_length=100)
    user_type = models.CharField(
        max_length=20, choices=[("STUDENT", "Student"), ("STAFF", "Staff")]
    )
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)

    # Balance tracking
    total_allocated = models.PositiveIntegerField(default=0)
    used_days = models.PositiveIntegerField(default=0)
    pending_days = models.PositiveIntegerField(default=0)  # Days in pending requests

    # Period tracking
    year = models.PositiveIntegerField(default=timezone.now().year)
    academic_year = models.CharField(max_length=20, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "leave_balances"
        unique_together = ["user_id", "leave_type", "year"]
        indexes = [
            models.Index(fields=["user_id"]),
            models.Index(fields=["year"]),
            models.Index(fields=["user_type"]),
        ]

    def __str__(self):
        return f"{self.user_id} - {self.leave_type.name} ({self.year})"

    @property
    def available_days(self):
        """Calculate available leave days"""
        return max(0, self.total_allocated - self.used_days - self.pending_days)

    @property
    def utilization_percentage(self):
        """Calculate leave utilization percentage"""
        if self.total_allocated == 0:
            return 0
        return (self.used_days / self.total_allocated) * 100


class LeaveApproval(models.Model):
    """Model for leave approval workflow"""

    ACTION_CHOICES = [
        ("SUBMITTED", "Submitted"),
        ("REVIEWED", "Reviewed"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
        ("WITHDRAWN", "Withdrawn"),
        ("MODIFIED", "Modified"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    leave_request = models.ForeignKey(
        LeaveRequest, on_delete=models.CASCADE, related_name="approvals"
    )

    # Approver information
    approver_id = models.CharField(max_length=100)
    approver_name = models.CharField(max_length=200)
    approver_type = models.CharField(max_length=20)  # HOD, STAFF, ADMIN, etc.

    # Action details
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    comments = models.TextField(blank=True)
    action_date = models.DateTimeField(auto_now_add=True)

    # Additional data
    previous_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = "leave_approvals"
        ordering = ["-action_date"]
        indexes = [
            models.Index(fields=["leave_request"]),
            models.Index(fields=["approver_id"]),
            models.Index(fields=["action"]),
            models.Index(fields=["action_date"]),
        ]

    def __str__(self):
        return f"{self.leave_request} - {self.action} by {self.approver_name}"


class LeavePolicy(models.Model):
    """Model for leave policies and rules"""

    POLICY_TYPES = [
        ("ANNUAL_ALLOCATION", "Annual Allocation"),
        ("CARRYOVER", "Carryover Rules"),
        ("APPROVAL_HIERARCHY", "Approval Hierarchy"),
        ("BLACKOUT_DATES", "Blackout Dates"),
        ("MINIMUM_NOTICE", "Minimum Notice Period"),
        ("MAXIMUM_CONSECUTIVE", "Maximum Consecutive Days"),
        ("OTHER", "Other Policy"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    policy_type = models.CharField(max_length=30, choices=POLICY_TYPES)
    description = models.TextField()

    # Applicability
    leave_type = models.ForeignKey(
        LeaveType, on_delete=models.CASCADE, null=True, blank=True
    )
    user_type = models.CharField(
        max_length=20,
        choices=[("STUDENT", "Student"), ("STAFF", "Staff"), ("BOTH", "Both")],
    )

    # Policy rules (JSON field for flexibility)
    rules = models.JSONField(default=dict, help_text="Policy rules in JSON format")

    # Metadata
    is_active = models.BooleanField(default=True)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "leave_policies"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["policy_type"]),
            models.Index(fields=["user_type"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["effective_from"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_policy_type_display()})"
