from django.contrib import admin

from .models import (Attendance, AttendanceReport, AttendanceSession,
                     AttendanceSettings)


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "session_date",
        "start_time",
        "end_time",
        "status",
        "course_id",
        "subject_id",
    ]
    list_filter = ["status", "session_date", "course_id"]
    search_fields = ["title", "description"]
    ordering = ["-session_date", "-start_time"]
    date_hierarchy = "session_date"


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = [
        "student_id",
        "session",
        "status",
        "check_in_time",
        "marked_by_staff_id",
    ]
    list_filter = ["status", "session__session_date", "session__course_id"]
    search_fields = ["student_id", "session__title"]
    ordering = ["-created_at"]
    raw_id_fields = ["session"]


@admin.register(AttendanceReport)
class AttendanceReportAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "report_type",
        "start_date",
        "end_date",
        "generated_by_staff_id",
        "generated_at",
    ]
    list_filter = ["report_type", "start_date", "course_id"]
    search_fields = ["title"]
    ordering = ["-generated_at"]
    date_hierarchy = "generated_at"


@admin.register(AttendanceSettings)
class AttendanceSettingsAdmin(admin.ModelAdmin):
    list_display = [
        "course_id",
        "subject_id",
        "late_threshold_minutes",
        "auto_absent_minutes",
        "send_absent_notifications",
    ]
    list_filter = ["send_absent_notifications", "send_late_notifications"]
    ordering = ["course_id", "subject_id"]
