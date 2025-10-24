from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class CustomUser(AbstractUser):
    """Extended User model with user type classification"""

    USER_TYPE_CHOICES = ((1, "HOD"), (2, "Staff"), (3, "Student"))

    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users_customuser"

    def __str__(self):
        return f"{self.username} - {self.get_user_type_display()}"


class AdminHOD(models.Model):
    """Head of Department profile"""

    id = models.AutoField(primary_key=True)
    admin = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name="admin_profile"
    )
    department = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users_adminhod"
        verbose_name = "Admin HOD"
        verbose_name_plural = "Admin HODs"

    def __str__(self):
        return f"HOD: {self.admin.get_full_name()}"


class Staff(models.Model):
    """Staff profile"""

    id = models.AutoField(primary_key=True)
    admin = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name="staff_profile"
    )
    address = models.TextField(blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    employee_id = models.CharField(max_length=20, unique=True, blank=True)
    department = models.CharField(max_length=100, blank=True)
    designation = models.CharField(max_length=100, blank=True)
    date_of_joining = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users_staff"
        verbose_name = "Staff"
        verbose_name_plural = "Staff"

    def __str__(self):
        return f"Staff: {self.admin.get_full_name()}"


class Student(models.Model):
    """Student profile"""

    GENDER_CHOICES = (("M", "Male"), ("F", "Female"), ("O", "Other"))

    id = models.AutoField(primary_key=True)
    admin = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name="student_profile"
    )
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    profile_pic = models.ImageField(upload_to="profile_pics/", null=True, blank=True)
    address = models.TextField(blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    student_id = models.CharField(max_length=20, unique=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    guardian_name = models.CharField(max_length=100, blank=True)
    guardian_phone = models.CharField(max_length=15, blank=True)

    # These will be foreign keys to other services in microservices architecture
    course_id = models.CharField(
        max_length=50, blank=True
    )  # Reference to Academic Service
    session_year_id = models.CharField(
        max_length=50, blank=True
    )  # Reference to Academic Service

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users_student"
        verbose_name = "Student"
        verbose_name_plural = "Students"

    def __str__(self):
        return f"Student ID: {self.student_id}"


# Django Signals for automatic profile creation
@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    """Automatically create user profile based on user type"""
    if created:
        if instance.user_type == 1:  # HOD
            AdminHOD.objects.create(admin=instance)
        elif instance.user_type == 2:  # Staff
            Staff.objects.create(admin=instance)
        # Student profiles are created manually with additional data


@receiver(post_save, sender=CustomUser)
def save_user_profile(sender, instance, **kwargs):
    """Save user profile when user is saved"""
    try:
        if instance.user_type == 1 and hasattr(instance, "admin_profile"):
            instance.admin_profile.save()
        elif instance.user_type == 2 and hasattr(instance, "staff_profile"):
            instance.staff_profile.save()
        elif instance.user_type == 3 and hasattr(instance, "student_profile"):
            instance.student_profile.save()
    except Exception:
        # Profile doesn't exist yet, will be created by create_user_profile signal
        pass
