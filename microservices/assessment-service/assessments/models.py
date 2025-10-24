import json
import uuid

from django.core.validators import (FileExtensionValidator, MaxValueValidator,
                                    MinValueValidator)
from django.db import models
from django.utils import timezone


class Assignment(models.Model):
    """Model for assignments and homework"""

    ASSIGNMENT_TYPES = [
        ("HOMEWORK", "Homework"),
        ("PROJECT", "Project"),
        ("QUIZ", "Quiz"),
        ("LAB", "Lab Assignment"),
        ("PRESENTATION", "Presentation"),
        ("ESSAY", "Essay"),
        ("RESEARCH", "Research Paper"),
    ]

    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("PUBLISHED", "Published"),
        ("CLOSED", "Closed"),
        ("GRADED", "Graded"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField()
    assignment_type = models.CharField(
        max_length=20, choices=ASSIGNMENT_TYPES, default="HOMEWORK"
    )

    # Academic context
    course_id = models.CharField(max_length=100)
    course_name = models.CharField(max_length=200)
    subject_id = models.CharField(max_length=100)
    subject_name = models.CharField(max_length=200)
    academic_year = models.CharField(max_length=20)
    semester = models.CharField(max_length=20)

    # Assignment details
    instructions = models.TextField(blank=True)
    max_marks = models.PositiveIntegerField(default=100)
    passing_marks = models.PositiveIntegerField(default=40)
    weightage = models.DecimalField(
        max_digits=5, decimal_places=2, default=10.0
    )  # Percentage weightage in final grade

    # Timing
    created_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField()
    late_submission_allowed = models.BooleanField(default=True)
    late_penalty_per_day = models.PositiveIntegerField(
        default=5
    )  # Percentage penalty per day

    # Files and resources
    attachment = models.FileField(upload_to="assignments/", blank=True, null=True)
    reference_materials = models.JSONField(
        default=list, blank=True
    )  # List of URLs or file references

    # Settings
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="DRAFT")
    allow_multiple_submissions = models.BooleanField(default=False)
    show_grades_immediately = models.BooleanField(default=False)
    plagiarism_check_enabled = models.BooleanField(default=False)

    # Creator info
    created_by = models.CharField(max_length=100)  # Staff/Teacher ID
    creator_name = models.CharField(max_length=200)

    # Metadata
    submission_count = models.PositiveIntegerField(default=0)
    average_grade = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    completion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)

    class Meta:
        db_table = "assignments"
        indexes = [
            models.Index(fields=["course_id"]),
            models.Index(fields=["subject_id"]),
            models.Index(fields=["created_by"]),
            models.Index(fields=["status"]),
            models.Index(fields=["due_date"]),
            models.Index(fields=["academic_year", "semester"]),
        ]
        ordering = ["-created_date"]

    def __str__(self):
        return f"{self.title} - {self.course_name}"

    @property
    def is_overdue(self):
        return timezone.now() > self.due_date and self.status != "CLOSED"

    @property
    def days_until_due(self):
        if self.due_date:
            delta = self.due_date - timezone.now()
            return delta.days
        return None


class Submission(models.Model):
    """Model for assignment submissions"""

    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("SUBMITTED", "Submitted"),
        ("LATE", "Late Submission"),
        ("GRADED", "Graded"),
        ("RETURNED", "Returned for Revision"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.ForeignKey(
        Assignment, on_delete=models.CASCADE, related_name="submissions"
    )

    # Student info
    student_id = models.CharField(max_length=100)
    student_name = models.CharField(max_length=200)
    student_email = models.EmailField()

    # Submission details
    submission_text = models.TextField(blank=True)
    attachment = models.FileField(upload_to="submissions/", blank=True, null=True)
    additional_files = models.JSONField(
        default=list, blank=True
    )  # List of additional file paths

    # Timing
    submitted_at = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    is_late = models.BooleanField(default=False)
    days_late = models.PositiveIntegerField(default=0)

    # Grading
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="DRAFT")
    marks_obtained = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    grade = models.CharField(max_length=5, blank=True)  # A+, A, B+, etc.
    percentage = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )

    # Feedback
    teacher_feedback = models.TextField(blank=True)
    graded_by = models.CharField(max_length=100, blank=True)
    graded_at = models.DateTimeField(null=True, blank=True)

    # Plagiarism and quality checks
    plagiarism_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    word_count = models.PositiveIntegerField(null=True, blank=True)

    # Metadata
    attempt_number = models.PositiveIntegerField(default=1)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = "submissions"
        indexes = [
            models.Index(fields=["assignment"]),
            models.Index(fields=["student_id"]),
            models.Index(fields=["status"]),
            models.Index(fields=["submitted_at"]),
            models.Index(fields=["is_late"]),
        ]
        unique_together = ["assignment", "student_id", "attempt_number"]
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.assignment.title} - {self.student_name}"

    def save(self, *args, **kwargs):
        # Calculate if submission is late
        if self.assignment.due_date and self.submitted_at:
            if self.submitted_at > self.assignment.due_date:
                self.is_late = True
                delta = self.submitted_at - self.assignment.due_date
                self.days_late = delta.days

        # Calculate percentage if marks are available
        if self.marks_obtained is not None and self.assignment.max_marks:
            self.percentage = (self.marks_obtained / self.assignment.max_marks) * 100

        super().save(*args, **kwargs)


class Exam(models.Model):
    """Model for exams and tests"""

    EXAM_TYPES = [
        ("MIDTERM", "Midterm Exam"),
        ("FINAL", "Final Exam"),
        ("QUIZ", "Quiz"),
        ("TEST", "Class Test"),
        ("PRACTICAL", "Practical Exam"),
        ("VIVA", "Viva/Oral Exam"),
    ]

    STATUS_CHOICES = [
        ("SCHEDULED", "Scheduled"),
        ("ONGOING", "Ongoing"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
        ("POSTPONED", "Postponed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    exam_type = models.CharField(max_length=20, choices=EXAM_TYPES)

    # Academic context
    course_id = models.CharField(max_length=100)
    course_name = models.CharField(max_length=200)
    subject_id = models.CharField(max_length=100)
    subject_name = models.CharField(max_length=200)
    academic_year = models.CharField(max_length=20)
    semester = models.CharField(max_length=20)

    # Exam details
    max_marks = models.PositiveIntegerField(default=100)
    passing_marks = models.PositiveIntegerField(default=40)
    duration_minutes = models.PositiveIntegerField(default=180)  # 3 hours default
    weightage = models.DecimalField(
        max_digits=5, decimal_places=2, default=30.0
    )  # Percentage weightage in final grade

    # Scheduling
    exam_date = models.DateTimeField()
    end_time = models.DateTimeField()
    venue = models.CharField(max_length=200, blank=True)
    invigilator = models.CharField(max_length=200, blank=True)

    # Settings
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="SCHEDULED"
    )
    instructions = models.TextField(blank=True)
    materials_allowed = models.JSONField(
        default=list, blank=True
    )  # List of allowed materials

    # Results
    total_students = models.PositiveIntegerField(default=0)
    appeared_students = models.PositiveIntegerField(default=0)
    passed_students = models.PositiveIntegerField(default=0)
    average_marks = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    highest_marks = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    lowest_marks = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )

    # Creator info
    created_by = models.CharField(max_length=100)
    creator_name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "exams"
        indexes = [
            models.Index(fields=["course_id"]),
            models.Index(fields=["subject_id"]),
            models.Index(fields=["exam_date"]),
            models.Index(fields=["status"]),
            models.Index(fields=["academic_year", "semester"]),
        ]
        ordering = ["exam_date"]

    def __str__(self):
        return (
            f"{self.title} - {self.course_name} ({self.exam_date.strftime('%Y-%m-%d')})"
        )


class Grade(models.Model):
    """Model for storing grades and results"""

    GRADE_TYPES = [
        ("ASSIGNMENT", "Assignment Grade"),
        ("EXAM", "Exam Grade"),
        ("QUIZ", "Quiz Grade"),
        ("PROJECT", "Project Grade"),
        ("FINAL", "Final Grade"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Student info
    student_id = models.CharField(max_length=100)
    student_name = models.CharField(max_length=200)
    student_email = models.EmailField()

    # Academic context
    course_id = models.CharField(max_length=100)
    course_name = models.CharField(max_length=200)
    subject_id = models.CharField(max_length=100)
    subject_name = models.CharField(max_length=200)
    academic_year = models.CharField(max_length=20)
    semester = models.CharField(max_length=20)

    # Grade details
    grade_type = models.CharField(max_length=20, choices=GRADE_TYPES)
    assessment_id = models.CharField(max_length=100)  # ID of assignment/exam
    assessment_title = models.CharField(max_length=200)

    # Scoring
    marks_obtained = models.DecimalField(max_digits=5, decimal_places=2)
    max_marks = models.DecimalField(max_digits=5, decimal_places=2)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    letter_grade = models.CharField(max_length=5)  # A+, A, B+, B, C+, C, D, F
    grade_points = models.DecimalField(
        max_digits=3, decimal_places=2
    )  # GPA points (4.0 scale)

    # Status and feedback
    is_passed = models.BooleanField(default=False)
    remarks = models.TextField(blank=True)
    teacher_feedback = models.TextField(blank=True)

    # Grading info
    graded_by = models.CharField(max_length=100)
    grader_name = models.CharField(max_length=200)
    graded_at = models.DateTimeField()

    # Metadata
    weightage = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.0
    )  # Weightage in final grade
    is_final_grade = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "grades"
        indexes = [
            models.Index(fields=["student_id"]),
            models.Index(fields=["course_id"]),
            models.Index(fields=["subject_id"]),
            models.Index(fields=["grade_type"]),
            models.Index(fields=["academic_year", "semester"]),
            models.Index(fields=["is_final_grade"]),
        ]
        unique_together = ["student_id", "assessment_id", "grade_type"]
        ordering = ["-graded_at"]

    def __str__(self):
        return f"{self.student_name} - {self.assessment_title} ({self.letter_grade})"

    def save(self, *args, **kwargs):
        # Calculate percentage
        if self.marks_obtained is not None and self.max_marks:
            self.percentage = (self.marks_obtained / self.max_marks) * 100

        # Determine if passed
        if self.percentage >= 40:  # Default passing percentage
            self.is_passed = True

        super().save(*args, **kwargs)


class GradeScale(models.Model):
    """Model for defining grading scales and criteria"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    # Academic context
    course_id = models.CharField(max_length=100, blank=True)
    subject_id = models.CharField(max_length=100, blank=True)
    academic_year = models.CharField(max_length=20)
    semester = models.CharField(max_length=20, blank=True)

    # Scale definition
    scale_data = models.JSONField(default=dict)  # JSON defining grade boundaries
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    # Metadata
    created_by = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "grade_scales"
        indexes = [
            models.Index(fields=["course_id"]),
            models.Index(fields=["subject_id"]),
            models.Index(fields=["is_default"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.academic_year}"


class StudentResult(models.Model):
    """Model for consolidated student results and transcripts"""

    RESULT_STATUS = [
        ("DRAFT", "Draft"),
        ("PUBLISHED", "Published"),
        ("WITHHELD", "Withheld"),
        ("CANCELLED", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Student info
    student_id = models.CharField(max_length=100)
    student_name = models.CharField(max_length=200)
    student_email = models.EmailField()

    # Academic context
    course_id = models.CharField(max_length=100)
    course_name = models.CharField(max_length=200)
    academic_year = models.CharField(max_length=20)
    semester = models.CharField(max_length=20)

    # Results summary
    total_subjects = models.PositiveIntegerField(default=0)
    subjects_passed = models.PositiveIntegerField(default=0)
    subjects_failed = models.PositiveIntegerField(default=0)

    # GPA calculation
    total_credits = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    earned_credits = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    semester_gpa = models.DecimalField(
        max_digits=3, decimal_places=2, null=True, blank=True
    )
    cumulative_gpa = models.DecimalField(
        max_digits=3, decimal_places=2, null=True, blank=True
    )

    # Overall performance
    overall_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    overall_grade = models.CharField(max_length=5, blank=True)
    class_rank = models.PositiveIntegerField(null=True, blank=True)

    # Status
    result_status = models.CharField(
        max_length=20, choices=RESULT_STATUS, default="DRAFT"
    )
    is_promoted = models.BooleanField(default=False)
    remarks = models.TextField(blank=True)

    # Detailed results
    subject_results = models.JSONField(default=dict)  # Detailed subject-wise results

    # Metadata
    generated_by = models.CharField(max_length=100)
    generated_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "student_results"
        indexes = [
            models.Index(fields=["student_id"]),
            models.Index(fields=["course_id"]),
            models.Index(fields=["academic_year", "semester"]),
            models.Index(fields=["result_status"]),
            models.Index(fields=["semester_gpa"]),
        ]
        unique_together = ["student_id", "course_id", "academic_year", "semester"]
        ordering = ["-generated_at"]

    def __str__(self):
        return f"{self.student_name} - {self.course_name} ({self.academic_year} {self.semester})"
