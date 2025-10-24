from datetime import datetime

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from .models import Course, Enrollment, SessionYear, Subject, SubjectEnrollment
from .serializers import (CourseDetailSerializer, CourseSerializer,
                          EnrollmentDetailSerializer, EnrollmentSerializer,
                          SessionYearSerializer, SubjectEnrollmentSerializer,
                          SubjectSerializer)


@api_view(["GET"])
def health_check(request):
    """Health check endpoint"""
    return Response(
        {
            "status": "healthy",
            "service": "academic-service",
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


class SessionYearListCreateView(generics.ListCreateAPIView):
    """List and create session years"""

    queryset = SessionYear.objects.all()
    serializer_class = SessionYearSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["is_active"]
    search_fields = ["name"]
    ordering_fields = ["start_date", "created_at"]
    ordering = ["-start_date"]


class SessionYearDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, delete session year"""

    queryset = SessionYear.objects.all()
    serializer_class = SessionYearSerializer


class CourseListCreateView(generics.ListCreateAPIView):
    """List and create courses"""

    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["course_type", "is_active"]
    search_fields = ["name", "code", "description"]
    ordering_fields = ["name", "code", "created_at"]
    ordering = ["name"]


class CourseDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, delete course with subjects"""

    queryset = Course.objects.all()
    serializer_class = CourseDetailSerializer


class SubjectListCreateView(generics.ListCreateAPIView):
    """List and create subjects"""

    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["course", "subject_type", "semester", "is_active"]
    search_fields = ["name", "code", "description"]
    ordering_fields = ["name", "code", "semester", "created_at"]
    ordering = ["course", "semester", "name"]


class SubjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, delete subject"""

    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer


class EnrollmentListCreateView(generics.ListCreateAPIView):
    """List and create enrollments"""

    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["student_id", "course", "session_year", "status"]
    search_fields = ["course__name", "course__code"]
    ordering_fields = ["enrollment_date", "created_at"]
    ordering = ["-enrollment_date"]


class EnrollmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, delete enrollment with subject enrollments"""

    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentDetailSerializer


class SubjectEnrollmentListCreateView(generics.ListCreateAPIView):
    """List and create subject enrollments"""

    queryset = SubjectEnrollment.objects.all()
    serializer_class = SubjectEnrollmentSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["enrollment__student_id", "subject", "status"]
    search_fields = ["subject__name", "subject__code"]
    ordering_fields = ["enrollment_date", "created_at"]
    ordering = ["-enrollment_date"]


class SubjectEnrollmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, delete subject enrollment"""

    queryset = SubjectEnrollment.objects.all()
    serializer_class = SubjectEnrollmentSerializer


@api_view(["GET"])
def student_enrollments(request, student_id):
    """Get all enrollments for a specific student"""
    enrollments = Enrollment.objects.filter(student_id=student_id)
    serializer = EnrollmentDetailSerializer(enrollments, many=True)
    return Response(serializer.data)


@api_view(["GET"])
def course_subjects(request, course_id):
    """Get all subjects for a specific course"""
    try:
        course = Course.objects.get(id=course_id)
        subjects = course.subjects.filter(is_active=True)
        serializer = SubjectSerializer(subjects, many=True)
        return Response(serializer.data)
    except Course.DoesNotExist:
        return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)


@api_view(["GET"])
def active_session(request):
    """Get the current active session"""
    try:
        session = SessionYear.objects.get(is_active=True)
        serializer = SessionYearSerializer(session)
        return Response(serializer.data)
    except SessionYear.DoesNotExist:
        return Response(
            {"error": "No active session found"}, status=status.HTTP_404_NOT_FOUND
        )


@api_view(["POST"])
def enroll_student(request):
    """Enroll a student in a course"""
    serializer = EnrollmentSerializer(data=request.data)
    if serializer.is_valid():
        enrollment = serializer.save()
        return Response(
            EnrollmentDetailSerializer(enrollment).data, status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def enroll_subject(request):
    """Enroll a student in a subject"""
    serializer = SubjectEnrollmentSerializer(data=request.data)
    if serializer.is_valid():
        subject_enrollment = serializer.save()
        return Response(
            SubjectEnrollmentSerializer(subject_enrollment).data,
            status=status.HTTP_201_CREATED,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
