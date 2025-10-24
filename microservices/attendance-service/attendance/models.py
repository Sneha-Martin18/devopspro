from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class AttendanceSession(models.Model):
    """Model for attendance sessions/classes"""

    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("ongoing", "Ongoing"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    # External references (from other microservices)
    course_id = models.IntegerField(help_text="Course ID from Academic Service")
    subject_id = models.IntegerField(help_text="Subject ID from Academic Service")
    session_year_id = models.IntegerField(
        help_text="Session Year ID from Academic Service"
    )
    staff_id = models.IntegerField(help_text="Staff ID from User Management Service")

    # Session details
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    session_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="scheduled"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-session_date", "-start_time"]
        indexes = [
            models.Index(fields=["course_id", "subject_id"]),
            models.Index(fields=["session_date"]),
            models.Index(fields=["staff_id"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.session_date}"

    @property
    def duration_minutes(self):
        """Calculate session duration in minutes"""
        if self.start_time and self.end_time:
            start_datetime = timezone.datetime.combine(
                timezone.datetime.today(), self.start_time
            )
            end_datetime = timezone.datetime.combine(
                timezone.datetime.today(), self.end_time
            )
            return int((end_datetime - start_datetime).total_seconds() / 60)
        return 0


class Attendance(models.Model):
    """Model for individual student attendance records"""

    STATUS_CHOICES = [
        ("present", "Present"),
        ("absent", "Absent"),
        ("late", "Late"),
        ("excused", "Excused"),
    ]

    # References
    session = models.ForeignKey(
        AttendanceSession, on_delete=models.CASCADE, related_name="attendances"
    )
    student_id = models.IntegerField(
        help_text="Student ID from User Management Service"
    )

    # Attendance details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, help_text="Additional notes about attendance")

    # Metadata
    marked_by_staff_id = models.IntegerField(help_text="Staff ID who marked attendance")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["session", "student_id"]
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["student_id", "status"]),
            models.Index(fields=["session", "status"]),
        ]

    def __str__(self):
        return f"Student {self.student_id} - {self.session.title} - {self.status}"

    @property
    def is_present(self):
        """Check if student was present (including late)"""
        return self.status in ["present", "late"]


class AttendanceReport(models.Model):
    """Model for attendance reports and analytics"""

    REPORT_TYPES = [
        ("daily", "Daily Report"),
        ("weekly", "Weekly Report"),
        ("monthly", "Monthly Report"),
        ("subject", "Subject Report"),
        ("student", "Student Report"),
    ]

    # Report details
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    title = models.CharField(max_length=200)

    # Filters
    course_id = models.IntegerField(null=True, blank=True)
    subject_id = models.IntegerField(null=True, blank=True)
    student_id = models.IntegerField(null=True, blank=True)
    staff_id = models.IntegerField(null=True, blank=True)

    # Date range
    start_date = models.DateField()
    end_date = models.DateField()

    # Report data (JSON field for flexibility)
    report_data = models.JSONField(default=dict, help_text="Report statistics and data")

    # Metadata
    generated_by_staff_id = models.IntegerField(
        help_text="Staff ID who generated report"
    )
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-generated_at"]
        indexes = [
            models.Index(fields=["report_type", "start_date"]),
            models.Index(fields=["course_id", "subject_id"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.start_date} to {self.end_date})"


class AttendanceSettings(models.Model):
    """Model for attendance system settings"""

    # Course/Subject specific settings
    course_id = models.IntegerField(null=True, blank=True)
    subject_id = models.IntegerField(null=True, blank=True)

    # Attendance rules
    late_threshold_minutes = models.IntegerField(
        default=15,
        validators=[MinValueValidator(0), MaxValueValidator(60)],
        help_text="Minutes after start time to mark as late",
    )
    auto_absent_minutes = models.IntegerField(
        default=30,
        validators=[MinValueValidator(0), MaxValueValidator(120)],
        help_text="Minutes after start time to automatically mark as absent",
    )

    # Notification settings
    send_absent_notifications = models.BooleanField(default=True)
    send_late_notifications = models.BooleanField(default=False)

    # Metadata
    created_by_staff_id = models.IntegerField(help_text="Staff ID who created settings")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["course_id", "subject_id"]
        verbose_name_plural = "Attendance Settings"

    def __str__(self):
        if self.course_id and self.subject_id:
            return f"Settings for Course {self.course_id} - Subject {self.subject_id}"
        elif self.course_id:
            return f"Settings for Course {self.course_id}"
        return "Global Attendance Settings"
