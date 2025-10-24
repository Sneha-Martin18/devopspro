import uuid
from datetime import datetime, timedelta

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class FeedbackCategory(models.Model):
    """Model for feedback categories"""

    CATEGORY_TYPES = [
        ("COURSE", "Course Feedback"),
        ("INSTRUCTOR", "Instructor Feedback"),
        ("FACILITY", "Facility Feedback"),
        ("SERVICE", "Service Feedback"),
        ("ACADEMIC", "Academic Feedback"),
        ("ADMINISTRATIVE", "Administrative Feedback"),
        ("TECHNICAL", "Technical Support"),
        ("GENERAL", "General Feedback"),
        ("COMPLAINT", "Complaint"),
        ("SUGGESTION", "Suggestion"),
    ]

    TARGET_AUDIENCE = [
        ("STUDENT", "Students"),
        ("STAFF", "Staff"),
        ("BOTH", "Both"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    category_type = models.CharField(max_length=20, choices=CATEGORY_TYPES)
    description = models.TextField(blank=True)
    target_audience = models.CharField(
        max_length=10, choices=TARGET_AUDIENCE, default="BOTH"
    )
    is_active = models.BooleanField(default=True)
    requires_moderation = models.BooleanField(default=True)
    allow_anonymous = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "feedback_categories"
        ordering = ["display_order", "name"]
        indexes = [
            models.Index(fields=["category_type"]),
            models.Index(fields=["target_audience"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["display_order"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_category_type_display()})"


class Feedback(models.Model):
    """Model for feedback submissions"""

    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("SUBMITTED", "Submitted"),
        ("UNDER_REVIEW", "Under Review"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("RESOLVED", "Resolved"),
        ("CLOSED", "Closed"),
    ]

    PRIORITY_CHOICES = [
        ("LOW", "Low"),
        ("MEDIUM", "Medium"),
        ("HIGH", "High"),
        ("URGENT", "Urgent"),
    ]

    SENTIMENT_CHOICES = [
        ("POSITIVE", "Positive"),
        ("NEUTRAL", "Neutral"),
        ("NEGATIVE", "Negative"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # User information (stored as IDs for microservice architecture)
    user_id = models.CharField(
        max_length=100, blank=True, help_text="User ID from User Management Service"
    )
    user_type = models.CharField(
        max_length=20, choices=[("STUDENT", "Student"), ("STAFF", "Staff")], blank=True
    )
    user_name = models.CharField(
        max_length=200, blank=True, help_text="Cached user name for display"
    )
    user_email = models.EmailField(
        blank=True, help_text="Cached user email for notifications"
    )
    is_anonymous = models.BooleanField(default=False)

    # Feedback details
    category = models.ForeignKey(
        FeedbackCategory, on_delete=models.CASCADE, related_name="feedbacks"
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5",
    )

    # Target information (what/who the feedback is about)
    target_type = models.CharField(
        max_length=50, blank=True, help_text="Type of target (course, instructor, etc.)"
    )
    target_id = models.CharField(
        max_length=100, blank=True, help_text="ID of the target entity"
    )
    target_name = models.CharField(
        max_length=200, blank=True, help_text="Name of the target entity"
    )

    # Status and processing
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="SUBMITTED"
    )
    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default="MEDIUM"
    )
    sentiment = models.CharField(max_length=10, choices=SENTIMENT_CHOICES, blank=True)

    # Moderation and approval
    moderator_id = models.CharField(max_length=100, blank=True)
    moderator_name = models.CharField(max_length=200, blank=True)
    moderated_at = models.DateTimeField(null=True, blank=True)
    moderation_notes = models.TextField(blank=True)

    # Additional metadata
    attachments = models.JSONField(default=list, help_text="List of attachment URLs")
    tags = models.JSONField(default=list, help_text="List of tags for categorization")
    metadata = models.JSONField(default=dict, help_text="Additional metadata")

    # Academic context
    academic_year = models.CharField(max_length=20, blank=True)
    semester = models.CharField(max_length=20, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    # Visibility and publication
    is_public = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)

    class Meta:
        db_table = "feedbacks"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user_id"]),
            models.Index(fields=["status"]),
            models.Index(fields=["category"]),
            models.Index(fields=["rating"]),
            models.Index(fields=["priority"]),
            models.Index(fields=["target_type", "target_id"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["is_public"]),
            models.Index(fields=["is_featured"]),
        ]

    def __str__(self):
        user_display = self.user_name if not self.is_anonymous else "Anonymous"
        return f"{user_display} - {self.title} ({self.rating}/5)"

    def save(self, *args, **kwargs):
        if not self.submitted_at and self.status != "DRAFT":
            self.submitted_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def is_recent(self):
        """Check if feedback is recent (within last 7 days)"""
        return self.created_at >= timezone.now() - timedelta(days=7)

    @property
    def response_count(self):
        """Get count of responses to this feedback"""
        return self.responses.count()


class FeedbackResponse(models.Model):
    """Model for responses to feedback"""

    RESPONSE_TYPE_CHOICES = [
        ("OFFICIAL", "Official Response"),
        ("CLARIFICATION", "Clarification Request"),
        ("UPDATE", "Status Update"),
        ("RESOLUTION", "Resolution"),
        ("ACKNOWLEDGMENT", "Acknowledgment"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    feedback = models.ForeignKey(
        Feedback, on_delete=models.CASCADE, related_name="responses"
    )

    # Responder information
    responder_id = models.CharField(max_length=100)
    responder_name = models.CharField(max_length=200)
    responder_type = models.CharField(max_length=20)  # ADMIN, HOD, STAFF, etc.
    responder_designation = models.CharField(max_length=100, blank=True)

    # Response details
    response_type = models.CharField(
        max_length=20, choices=RESPONSE_TYPE_CHOICES, default="OFFICIAL"
    )
    message = models.TextField()
    attachments = models.JSONField(default=list, help_text="List of attachment URLs")

    # Visibility
    is_public = models.BooleanField(default=True)
    is_final = models.BooleanField(default=False, help_text="Mark as final response")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "feedback_responses"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["feedback"]),
            models.Index(fields=["responder_id"]),
            models.Index(fields=["response_type"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["is_public"]),
        ]

    def __str__(self):
        return f"Response by {self.responder_name} to {self.feedback.title}"


class FeedbackTemplate(models.Model):
    """Model for feedback form templates"""

    TEMPLATE_TYPES = [
        ("COURSE_EVALUATION", "Course Evaluation"),
        ("INSTRUCTOR_EVALUATION", "Instructor Evaluation"),
        ("FACILITY_FEEDBACK", "Facility Feedback"),
        ("SERVICE_FEEDBACK", "Service Feedback"),
        ("EXIT_FEEDBACK", "Exit Feedback"),
        ("CUSTOM", "Custom Template"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    template_type = models.CharField(max_length=30, choices=TEMPLATE_TYPES)
    description = models.TextField(blank=True)

    # Template structure (JSON format)
    questions = models.JSONField(
        default=list, help_text="List of questions in JSON format"
    )

    # Applicability
    target_audience = models.CharField(
        max_length=10, choices=FeedbackCategory.TARGET_AUDIENCE, default="BOTH"
    )
    categories = models.ManyToManyField(FeedbackCategory, blank=True)

    # Settings
    is_active = models.BooleanField(default=True)
    is_mandatory = models.BooleanField(default=False)
    allow_anonymous = models.BooleanField(default=True)

    # Scheduling
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)

    # Metadata
    created_by = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "feedback_templates"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["template_type"]),
            models.Index(fields=["target_audience"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["start_date", "end_date"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"


class FeedbackSurvey(models.Model):
    """Model for feedback surveys"""

    SURVEY_STATUS = [
        ("DRAFT", "Draft"),
        ("ACTIVE", "Active"),
        ("PAUSED", "Paused"),
        ("COMPLETED", "Completed"),
        ("ARCHIVED", "Archived"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    template = models.ForeignKey(
        FeedbackTemplate, on_delete=models.CASCADE, related_name="surveys"
    )

    # Target information
    target_type = models.CharField(
        max_length=50, help_text="Type of target (course, department, etc.)"
    )
    target_id = models.CharField(max_length=100, help_text="ID of the target entity")
    target_name = models.CharField(
        max_length=200, help_text="Name of the target entity"
    )

    # Participants
    target_audience = models.CharField(
        max_length=10, choices=FeedbackCategory.TARGET_AUDIENCE
    )
    participant_ids = models.JSONField(
        default=list, help_text="List of participant user IDs"
    )

    # Survey settings
    status = models.CharField(max_length=20, choices=SURVEY_STATUS, default="DRAFT")
    is_anonymous = models.BooleanField(default=True)
    allow_multiple_responses = models.BooleanField(default=False)

    # Scheduling
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    reminder_frequency = models.PositiveIntegerField(
        default=3, help_text="Reminder frequency in days"
    )

    # Academic context
    academic_year = models.CharField(max_length=20, blank=True)
    semester = models.CharField(max_length=20, blank=True)

    # Statistics
    total_participants = models.PositiveIntegerField(default=0)
    responses_count = models.PositiveIntegerField(default=0)
    completion_rate = models.FloatField(default=0.0)

    # Metadata
    created_by = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "feedback_surveys"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["target_type", "target_id"]),
            models.Index(fields=["start_date", "end_date"]),
            models.Index(fields=["created_by"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.target_name}"

    @property
    def is_active(self):
        """Check if survey is currently active"""
        now = timezone.now()
        return self.status == "ACTIVE" and self.start_date <= now <= self.end_date

    @property
    def days_remaining(self):
        """Get days remaining for survey"""
        if self.end_date:
            return (self.end_date.date() - timezone.now().date()).days
        return None


class FeedbackAnalytics(models.Model):
    """Model for feedback analytics and reports"""

    REPORT_TYPES = [
        ("DAILY", "Daily Report"),
        ("WEEKLY", "Weekly Report"),
        ("MONTHLY", "Monthly Report"),
        ("QUARTERLY", "Quarterly Report"),
        ("ANNUAL", "Annual Report"),
        ("CUSTOM", "Custom Report"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    title = models.CharField(max_length=200)

    # Report parameters
    start_date = models.DateField()
    end_date = models.DateField()
    categories = models.JSONField(default=list, help_text="List of category IDs")
    target_types = models.JSONField(default=list, help_text="List of target types")

    # Analytics data
    total_feedback = models.PositiveIntegerField(default=0)
    average_rating = models.FloatField(default=0.0)
    sentiment_distribution = models.JSONField(default=dict)
    category_breakdown = models.JSONField(default=dict)
    rating_distribution = models.JSONField(default=dict)
    response_rate = models.FloatField(default=0.0)

    # Insights and trends
    insights = models.JSONField(default=list, help_text="Generated insights")
    trends = models.JSONField(default=dict, help_text="Trend analysis")
    recommendations = models.JSONField(default=list, help_text="Recommendations")

    # Metadata
    generated_by = models.CharField(max_length=100)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "feedback_analytics"
        ordering = ["-generated_at"]
        indexes = [
            models.Index(fields=["report_type"]),
            models.Index(fields=["start_date", "end_date"]),
            models.Index(fields=["generated_by"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.start_date} to {self.end_date})"
