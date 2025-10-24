from datetime import datetime, timedelta

from django.db.models import Count, Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import (Attendance, AttendanceReport, AttendanceSession,
                     AttendanceSettings)
from .serializers import (AttendanceReportSerializer, AttendanceSerializer,
                          AttendanceSessionSerializer,
                          AttendanceSettingsSerializer,
                          AttendanceStatsSerializer, BulkAttendanceSerializer)


@api_view(["GET"])
def health_check(request):
    """Health check endpoint for Attendance Service"""
    return Response(
        {
            "status": "healthy",
            "service": "attendance-service",
            "timestamp": timezone.now().isoformat(),
        }
    )


class AttendanceSessionListCreateView(generics.ListCreateAPIView):
    """List all attendance sessions or create a new session"""

    queryset = AttendanceSession.objects.all()
    serializer_class = AttendanceSessionSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["course_id", "subject_id", "staff_id", "status", "session_date"]
    search_fields = ["title", "description"]
    ordering_fields = ["session_date", "start_time", "created_at"]
    ordering = ["-session_date", "-start_time"]


class AttendanceSessionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete an attendance session"""

    queryset = AttendanceSession.objects.all()
    serializer_class = AttendanceSessionSerializer


class AttendanceListCreateView(generics.ListCreateAPIView):
    """List all attendance records or create a new record"""

    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = [
        "student_id",
        "status",
        "session__course_id",
        "session__subject_id",
    ]
    ordering_fields = ["created_at", "session__session_date"]
    ordering = ["-created_at"]


class AttendanceDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete an attendance record"""

    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer


class StudentAttendanceView(generics.ListAPIView):
    """Get attendance records for a specific student"""

    serializer_class = AttendanceSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status", "session__course_id", "session__subject_id"]
    ordering = ["-session__session_date"]

    def get_queryset(self):
        student_id = self.kwargs["student_id"]
        return Attendance.objects.filter(student_id=student_id)


class SessionAttendanceView(generics.ListAPIView):
    """Get all attendance records for a specific session"""

    serializer_class = AttendanceSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status"]

    def get_queryset(self):
        session_id = self.kwargs["session_id"]
        return Attendance.objects.filter(session_id=session_id)


@api_view(["POST"])
def bulk_attendance_mark(request):
    """Mark attendance for multiple students in a session"""
    serializer = BulkAttendanceSerializer(data=request.data)
    if serializer.is_valid():
        session_id = serializer.validated_data["session_id"]
        attendances_data = serializer.validated_data["attendances"]
        marked_by_staff_id = serializer.validated_data["marked_by_staff_id"]

        try:
            session = AttendanceSession.objects.get(id=session_id)
        except AttendanceSession.DoesNotExist:
            return Response(
                {"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND
            )

        created_records = []
        updated_records = []

        for attendance_data in attendances_data:
            student_id = int(attendance_data["student_id"])
            attendance_status = attendance_data["status"]
            notes = attendance_data.get("notes", "")

            # Check if attendance already exists
            attendance, created = Attendance.objects.get_or_create(
                session=session,
                student_id=student_id,
                defaults={
                    "status": attendance_status,
                    "notes": notes,
                    "marked_by_staff_id": marked_by_staff_id,
                    "check_in_time": timezone.now()
                    if attendance_status in ["present", "late"]
                    else None,
                },
            )

            if not created:
                # Update existing record
                attendance.status = attendance_status
                attendance.notes = notes
                attendance.marked_by_staff_id = marked_by_staff_id
                if (
                    attendance_status in ["present", "late"]
                    and not attendance.check_in_time
                ):
                    attendance.check_in_time = timezone.now()
                attendance.save()
                updated_records.append(attendance.id)
            else:
                created_records.append(attendance.id)

        return Response(
            {
                "message": "Bulk attendance marked successfully",
                "created_records": len(created_records),
                "updated_records": len(updated_records),
                "total_processed": len(attendances_data),
            }
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def attendance_stats(request):
    """Get attendance statistics for a date range and filters"""
    # Get query parameters
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    course_id = request.GET.get("course_id")
    subject_id = request.GET.get("subject_id")
    student_id = request.GET.get("student_id")

    if not start_date or not end_date:
        return Response(
            {"error": "start_date and end_date are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        return Response(
            {"error": "Invalid date format. Use YYYY-MM-DD"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Build query filters
    filters = Q(session__session_date__range=[start_date, end_date])

    if course_id:
        filters &= Q(session__course_id=course_id)
    if subject_id:
        filters &= Q(session__subject_id=subject_id)
    if student_id:
        filters &= Q(student_id=student_id)

    # Get attendance statistics
    attendance_qs = Attendance.objects.filter(filters)

    stats = attendance_qs.aggregate(
        total_records=Count("id"),
        present_count=Count("id", filter=Q(status="present")),
        absent_count=Count("id", filter=Q(status="absent")),
        late_count=Count("id", filter=Q(status="late")),
        excused_count=Count("id", filter=Q(status="excused")),
    )

    # Calculate additional stats
    total_sessions = AttendanceSession.objects.filter(
        session_date__range=[start_date, end_date]
    ).count()

    if course_id:
        total_sessions = AttendanceSession.objects.filter(
            session_date__range=[start_date, end_date], course_id=course_id
        ).count()

    total_students = attendance_qs.values("student_id").distinct().count()

    # Calculate attendance percentage
    total_present = stats["present_count"] + stats["late_count"]
    total_records = stats["total_records"]
    attendance_percentage = (
        (total_present / total_records * 100) if total_records > 0 else 0
    )

    response_data = {
        "total_sessions": total_sessions,
        "total_students": total_students,
        "present_count": stats["present_count"],
        "absent_count": stats["absent_count"],
        "late_count": stats["late_count"],
        "excused_count": stats["excused_count"],
        "attendance_percentage": round(attendance_percentage, 2),
        "start_date": start_date,
        "end_date": end_date,
    }

    # Add filter info if provided
    if course_id:
        response_data["course_id"] = int(course_id)
    if subject_id:
        response_data["subject_id"] = int(subject_id)
    if student_id:
        response_data["student_id"] = int(student_id)

    return Response(response_data)


class AttendanceReportListCreateView(generics.ListCreateAPIView):
    """List all attendance reports or create a new report"""

    queryset = AttendanceReport.objects.all()
    serializer_class = AttendanceReportSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["report_type", "course_id", "subject_id", "student_id"]
    ordering = ["-generated_at"]


class AttendanceReportDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete an attendance report"""

    queryset = AttendanceReport.objects.all()
    serializer_class = AttendanceReportSerializer


class AttendanceSettingsListCreateView(generics.ListCreateAPIView):
    """List all attendance settings or create new settings"""

    queryset = AttendanceSettings.objects.all()
    serializer_class = AttendanceSettingsSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["course_id", "subject_id"]


class AttendanceSettingsDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete attendance settings"""

    queryset = AttendanceSettings.objects.all()
    serializer_class = AttendanceSettingsSerializer
