from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class SessionYear(models.Model):
    """Academic session/year model"""

    name = models.CharField(max_length=100, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.is_active:
            # Ensure only one active session at a time
            SessionYear.objects.filter(is_active=True).update(is_active=False)
        super().save(*args, **kwargs)


class Course(models.Model):
    """Course model"""

    COURSE_TYPES = [
        ("undergraduate", "Undergraduate"),
        ("postgraduate", "Postgraduate"),
        ("diploma", "Diploma"),
        ("certificate", "Certificate"),
    ]

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    course_type = models.CharField(
        max_length=20, choices=COURSE_TYPES, default="undergraduate"
    )
    duration_years = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    total_credits = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Subject(models.Model):
    """Subject model"""

    SUBJECT_TYPES = [
        ("core", "Core"),
        ("elective", "Elective"),
        ("practical", "Practical"),
        ("project", "Project"),
    ]

    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="subjects"
    )
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    subject_type = models.CharField(
        max_length=20, choices=SUBJECT_TYPES, default="core"
    )
    credits = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    semester = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["course", "semester", "name"]
        unique_together = ["course", "code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Enrollment(models.Model):
    """Student enrollment model"""

    ENROLLMENT_STATUS = [
        ("active", "Active"),
        ("completed", "Completed"),
        ("dropped", "Dropped"),
        ("suspended", "Suspended"),
    ]

    student_id = models.PositiveIntegerField()  # Reference to User Management Service
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="enrollments"
    )
    session_year = models.ForeignKey(
        SessionYear, on_delete=models.CASCADE, related_name="enrollments"
    )
    enrollment_date = models.DateField(auto_now_add=True)
    status = models.CharField(
        max_length=20, choices=ENROLLMENT_STATUS, default="active"
    )
    current_semester = models.PositiveIntegerField(
        default=1, validators=[MinValueValidator(1)]
    )
    completion_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-enrollment_date"]
        unique_together = ["student_id", "course", "session_year"]

    def __str__(self):
        return f"Student {self.student_id} - {self.course.code}"


class SubjectEnrollment(models.Model):
    """Subject-wise enrollment model"""

    ENROLLMENT_STATUS = [
        ("enrolled", "Enrolled"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("dropped", "Dropped"),
    ]

    enrollment = models.ForeignKey(
        Enrollment, on_delete=models.CASCADE, related_name="subject_enrollments"
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="enrollments"
    )
    enrollment_date = models.DateField(auto_now_add=True)
    status = models.CharField(
        max_length=20, choices=ENROLLMENT_STATUS, default="enrolled"
    )
    grade = models.CharField(max_length=5, blank=True)
    marks = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    completion_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-enrollment_date"]
        unique_together = ["enrollment", "subject"]

    def __str__(self):
        return f"{self.enrollment.student_id} - {self.subject.code}"
