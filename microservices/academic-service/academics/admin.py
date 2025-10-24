from django.contrib import admin

from .models import Course, Enrollment, SessionYear, Subject, SubjectEnrollment


@admin.register(SessionYear)
class SessionYearAdmin(admin.ModelAdmin):
    list_display = ["name", "start_date", "end_date", "is_active", "created_at"]
    list_filter = ["is_active", "start_date"]
    search_fields = ["name"]
    ordering = ["-start_date"]


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "name",
        "course_type",
        "duration_years",
        "total_credits",
        "is_active",
    ]
    list_filter = ["course_type", "is_active", "duration_years"]
    search_fields = ["name", "code", "description"]
    ordering = ["name"]


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "name",
        "course",
        "subject_type",
        "semester",
        "credits",
        "is_active",
    ]
    list_filter = ["course", "subject_type", "semester", "is_active"]
    search_fields = ["name", "code", "description"]
    ordering = ["course", "semester", "name"]


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = [
        "student_id",
        "course",
        "session_year",
        "status",
        "current_semester",
        "enrollment_date",
    ]
    list_filter = ["course", "session_year", "status", "enrollment_date"]
    search_fields = ["student_id", "course__name", "course__code"]
    ordering = ["-enrollment_date"]


@admin.register(SubjectEnrollment)
class SubjectEnrollmentAdmin(admin.ModelAdmin):
    list_display = [
        "get_student_id",
        "subject",
        "status",
        "grade",
        "marks",
        "enrollment_date",
    ]
    list_filter = ["subject", "status", "enrollment_date"]
    search_fields = ["enrollment__student_id", "subject__name", "subject__code"]
    ordering = ["-enrollment_date"]

    def get_student_id(self, obj):
        return obj.enrollment.student_id

    get_student_id.short_description = "Student ID"
