from django.utils import timezone
from rest_framework import serializers

from .models import (Attendance, AttendanceReport, AttendanceSession,
                     AttendanceSettings)


class AttendanceSessionSerializer(serializers.ModelSerializer):
    duration_minutes = serializers.ReadOnlyField()
    attendance_count = serializers.SerializerMethodField()
    present_count = serializers.SerializerMethodField()
    absent_count = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceSession
        fields = [
            "id",
            "course_id",
            "subject_id",
            "session_year_id",
            "staff_id",
            "title",
            "description",
            "session_date",
            "start_time",
            "end_time",
            "status",
            "duration_minutes",
            "attendance_count",
            "present_count",
            "absent_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("created_at", "updated_at")

    def get_attendance_count(self, obj):
        return obj.attendances.count()

    def get_present_count(self, obj):
        return obj.attendances.filter(status__in=["present", "late"]).count()

    def get_absent_count(self, obj):
        return obj.attendances.filter(status="absent").count()

    def validate(self, data):
        if data["start_time"] >= data["end_time"]:
            raise serializers.ValidationError("End time must be after start time")
        return data


class AttendanceSerializer(serializers.ModelSerializer):
    session_title = serializers.CharField(source="session.title", read_only=True)
    session_date = serializers.DateField(source="session.session_date", read_only=True)
    is_present = serializers.ReadOnlyField()

    class Meta:
        model = Attendance
        fields = [
            "id",
            "session",
            "student_id",
            "status",
            "check_in_time",
            "check_out_time",
            "notes",
            "marked_by_staff_id",
            "session_title",
            "session_date",
            "is_present",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("created_at", "updated_at")

    def validate(self, data):
        # Check if attendance already exists for this student and session
        if self.instance is None:  # Creating new record
            if Attendance.objects.filter(
                session=data["session"], student_id=data["student_id"]
            ).exists():
                raise serializers.ValidationError(
                    "Attendance already marked for this student in this session"
                )
        return data


class AttendanceReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceReport
        fields = [
            "id",
            "report_type",
            "title",
            "course_id",
            "subject_id",
            "student_id",
            "staff_id",
            "start_date",
            "end_date",
            "report_data",
            "generated_by_staff_id",
            "generated_at",
        ]
        read_only_fields = ("generated_at",)

    def validate(self, data):
        if data["start_date"] > data["end_date"]:
            raise serializers.ValidationError("Start date must be before end date")
        return data


class AttendanceSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceSettings
        fields = [
            "id",
            "course_id",
            "subject_id",
            "late_threshold_minutes",
            "auto_absent_minutes",
            "send_absent_notifications",
            "send_late_notifications",
            "created_by_staff_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("created_at", "updated_at")


class BulkAttendanceSerializer(serializers.Serializer):
    """Serializer for bulk attendance marking"""

    session_id = serializers.IntegerField()
    attendances = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField()), allow_empty=False
    )
    marked_by_staff_id = serializers.IntegerField()

    def validate_attendances(self, value):
        """Validate attendance records format"""
        for attendance in value:
            if "student_id" not in attendance or "status" not in attendance:
                raise serializers.ValidationError(
                    "Each attendance record must have 'student_id' and 'status'"
                )

            if attendance["status"] not in ["present", "absent", "late", "excused"]:
                raise serializers.ValidationError(
                    f"Invalid status: {attendance['status']}"
                )

        return value


class AttendanceStatsSerializer(serializers.Serializer):
    """Serializer for attendance statistics"""

    total_sessions = serializers.IntegerField()
    total_students = serializers.IntegerField()
    present_count = serializers.IntegerField()
    absent_count = serializers.IntegerField()
    late_count = serializers.IntegerField()
    excused_count = serializers.IntegerField()
    attendance_percentage = serializers.FloatField()

    # Date range
    start_date = serializers.DateField()
    end_date = serializers.DateField()

    # Optional filters
    course_id = serializers.IntegerField(required=False)
    subject_id = serializers.IntegerField(required=False)
    student_id = serializers.IntegerField(required=False)
