from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AdminHOD, CustomUser, Staff, Student


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Admin configuration for CustomUser"""

    list_display = [
        "username",
        "email",
        "first_name",
        "last_name",
        "user_type",
        "is_active",
        "date_joined",
    ]
    list_filter = ["user_type", "is_active", "date_joined"]
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering = ["-date_joined"]

    fieldsets = UserAdmin.fieldsets + (
        ("Additional Info", {"fields": ("user_type", "created_at", "updated_at")}),
    )
    readonly_fields = ["created_at", "updated_at"]


@admin.register(AdminHOD)
class AdminHODAdmin(admin.ModelAdmin):
    """Admin configuration for AdminHOD"""

    list_display = ["admin", "department", "phone_number", "created_at"]
    list_filter = ["department", "created_at"]
    search_fields = ["admin__username", "admin__email", "department"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    """Admin configuration for Staff"""

    list_display = [
        "admin",
        "employee_id",
        "department",
        "designation",
        "date_of_joining",
    ]
    list_filter = ["department", "designation", "date_of_joining"]
    search_fields = ["admin__username", "admin__email", "employee_id", "department"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    """Admin configuration for Student"""

    list_display = ["admin", "student_id", "gender", "course_id", "session_year_id"]
    list_filter = ["gender", "course_id", "session_year_id", "created_at"]
    search_fields = ["admin__username", "admin__email", "student_id"]
    readonly_fields = ["created_at", "updated_at"]


# UserSessionAdmin removed - session tracking disabled
