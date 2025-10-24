import logging

from django.db import transaction
from django.db.models import Avg, Count, Max, Min, Q, Sum
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (Assignment, Exam, Grade, GradeScale, StudentResult,
                     Submission)
from .serializers import (AssessmentAnalyticsSerializer,
                          AssignmentBulkCreateSerializer,
                          AssignmentCreateSerializer, AssignmentSerializer,
                          AssignmentStatsSerializer, BulkGradeSerializer,
                          CourseAssessmentSummarySerializer,
                          ExamResultsSerializer, ExamSerializer,
                          GradebookSerializer, GradeScaleSerializer,
                          GradeSerializer, StudentPerformanceSerializer,
                          StudentResultSerializer, SubmissionGradeSerializer,
                          SubmissionSerializer)
from .tasks import process_grade_calculation, send_assignment_notification

logger = logging.getLogger(__name__)


class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = [
        "assignment_type",
        "status",
        "course_id",
        "subject_id",
        "academic_year",
        "semester",
        "created_by",
    ]
    search_fields = ["title", "description", "course_name", "subject_name"]
    ordering_fields = ["created_date", "due_date", "max_marks", "title"]
    ordering = ["-created_date"]

    def get_serializer_class(self):
        if self.action == "create":
            return AssignmentCreateSerializer
        return AssignmentSerializer

    def perform_create(self, serializer):
        assignment = serializer.save()
        # Send notification asynchronously
        send_assignment_notification.delay(assignment.id, "CREATED")

    def perform_update(self, serializer):
        assignment = serializer.save()
        send_assignment_notification.delay(assignment.id, "UPDATED")

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        """Publish an assignment"""
        assignment = self.get_object()
        if assignment.status == "DRAFT":
            assignment.status = "PUBLISHED"
            assignment.save()
            send_assignment_notification.delay(assignment.id, "PUBLISHED")
            return Response({"message": "Assignment published successfully"})
        return Response(
            {"error": "Assignment is not in draft status"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        """Close an assignment for submissions"""
        assignment = self.get_object()
        if assignment.status == "PUBLISHED":
            assignment.status = "CLOSED"
            assignment.save()
            return Response({"message": "Assignment closed successfully"})
        return Response(
            {"error": "Assignment is not published"}, status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=["get"])
    def submissions(self, request, pk=None):
        """Get all submissions for an assignment"""
        assignment = self.get_object()
        submissions = assignment.submissions.all()

        # Apply filters
        status_filter = request.query_params.get("status")
        if status_filter:
            submissions = submissions.filter(status=status_filter)

        serializer = SubmissionSerializer(submissions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def statistics(self, request, pk=None):
        """Get assignment statistics"""
        assignment = self.get_object()
        submissions = assignment.submissions.all()

        stats = {
            "total_submissions": submissions.count(),
            "submitted": submissions.filter(status="SUBMITTED").count(),
            "graded": submissions.filter(status="GRADED").count(),
            "late_submissions": submissions.filter(is_late=True).count(),
            "average_grade": submissions.filter(marks_obtained__isnull=False).aggregate(
                avg=Avg("marks_obtained")
            )["avg"]
            or 0,
            "highest_grade": submissions.aggregate(max=Max("marks_obtained"))["max"]
            or 0,
            "lowest_grade": submissions.aggregate(min=Min("marks_obtained"))["min"]
            or 0,
        }

        return Response(stats)

    @action(detail=False, methods=["get"])
    def overdue(self, request):
        """Get overdue assignments"""
        overdue_assignments = self.queryset.filter(
            due_date__lt=timezone.now(), status="PUBLISHED"
        )
        serializer = self.get_serializer(overdue_assignments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def my_assignments(self, request):
        """Get assignments created by the current user"""
        user_id = request.query_params.get("user_id")
        if not user_id:
            return Response(
                {"error": "user_id parameter required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assignments = self.queryset.filter(created_by=user_id)
        serializer = self.get_serializer(assignments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def bulk_create(self, request):
        """Create multiple assignments at once"""
        serializer = AssignmentBulkCreateSerializer(data=request.data)
        if serializer.is_valid():
            assignments = serializer.save()
            response_serializer = AssignmentSerializer(assignments, many=True)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SubmissionViewSet(viewsets.ModelViewSet):
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = [
        "assignment",
        "student_id",
        "status",
        "is_late",
        "assignment__course_id",
        "assignment__subject_id",
        "assignment__academic_year",
    ]
    search_fields = ["student_name", "assignment__title", "submission_text"]
    ordering_fields = ["submitted_at", "marks_obtained", "percentage"]
    ordering = ["-submitted_at"]

    def perform_create(self, serializer):
        # Set attempt number
        assignment = serializer.validated_data["assignment"]
        student_id = serializer.validated_data["student_id"]

        last_attempt = (
            Submission.objects.filter(
                assignment=assignment, student_id=student_id
            ).aggregate(max_attempt=Max("attempt_number"))["max_attempt"]
            or 0
        )

        serializer.save(
            attempt_number=last_attempt + 1,
            ip_address=self.request.META.get("REMOTE_ADDR"),
        )

    @action(detail=True, methods=["post"])
    def grade(self, request, pk=None):
        """Grade a submission"""
        submission = self.get_object()
        serializer = SubmissionGradeSerializer(
            submission, data=request.data, partial=True
        )

        if serializer.is_valid():
            serializer.save(graded_at=timezone.now())

            # Create grade record
            Grade.objects.create(
                student_id=submission.student_id,
                student_name=submission.student_name,
                student_email=submission.student_email,
                course_id=submission.assignment.course_id,
                course_name=submission.assignment.course_name,
                subject_id=submission.assignment.subject_id,
                subject_name=submission.assignment.subject_name,
                academic_year=submission.assignment.academic_year,
                semester=submission.assignment.semester,
                grade_type="ASSIGNMENT",
                assessment_id=str(submission.assignment.id),
                assessment_title=submission.assignment.title,
                marks_obtained=submission.marks_obtained,
                max_marks=submission.assignment.max_marks,
                percentage=submission.percentage,
                letter_grade=submission.grade,
                grade_points=self._calculate_grade_points(submission.percentage),
                graded_by=request.data.get("graded_by", ""),
                grader_name=request.data.get("grader_name", ""),
                graded_at=timezone.now(),
                weightage=submission.assignment.weightage,
            )

            # Process grade calculation asynchronously
            process_grade_calculation.delay(
                submission.student_id, submission.assignment.course_id
            )

            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _calculate_grade_points(self, percentage):
        """Calculate grade points based on percentage"""
        if percentage >= 90:
            return 4.0
        elif percentage >= 80:
            return 3.5
        elif percentage >= 70:
            return 3.0
        elif percentage >= 60:
            return 2.5
        elif percentage >= 50:
            return 2.0
        elif percentage >= 40:
            return 1.5
        else:
            return 0.0

    @action(detail=False, methods=["get"])
    def pending_grading(self, request):
        """Get submissions pending grading"""
        pending = self.queryset.filter(status="SUBMITTED")
        serializer = self.get_serializer(pending, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def student_submissions(self, request):
        """Get submissions for a specific student"""
        student_id = request.query_params.get("student_id")
        if not student_id:
            return Response(
                {"error": "student_id parameter required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        submissions = self.queryset.filter(student_id=student_id)
        serializer = self.get_serializer(submissions, many=True)
        return Response(serializer.data)


class ExamViewSet(viewsets.ModelViewSet):
    queryset = Exam.objects.all()
    serializer_class = ExamSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = [
        "exam_type",
        "status",
        "course_id",
        "subject_id",
        "academic_year",
        "semester",
        "created_by",
    ]
    search_fields = ["title", "description", "course_name", "subject_name", "venue"]
    ordering_fields = ["exam_date", "created_at", "max_marks"]
    ordering = ["exam_date"]

    @action(detail=True, methods=["post"])
    def start_exam(self, request, pk=None):
        """Start an exam"""
        exam = self.get_object()
        if exam.status == "SCHEDULED":
            exam.status = "ONGOING"
            exam.save()
            return Response({"message": "Exam started successfully"})
        return Response(
            {"error": "Exam is not scheduled"}, status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=["post"])
    def complete_exam(self, request, pk=None):
        """Complete an exam"""
        exam = self.get_object()
        if exam.status == "ONGOING":
            exam.status = "COMPLETED"
            exam.save()
            return Response({"message": "Exam completed successfully"})
        return Response(
            {"error": "Exam is not ongoing"}, status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=["get"])
    def results(self, request, pk=None):
        """Get exam results and statistics"""
        exam = self.get_object()
        grades = Grade.objects.filter(assessment_id=str(exam.id), grade_type="EXAM")

        if not grades.exists():
            return Response({"message": "No results available yet"})

        stats = grades.aggregate(
            total_students=Count("id"),
            average_marks=Avg("marks_obtained"),
            highest_marks=Max("marks_obtained"),
            lowest_marks=Min("marks_obtained"),
            passed_students=Count("id", filter=Q(is_passed=True)),
        )

        grade_distribution = {}
        for grade in grades.values("letter_grade").annotate(
            count=Count("letter_grade")
        ):
            grade_distribution[grade["letter_grade"]] = grade["count"]

        student_results = []
        for grade in grades:
            student_results.append(
                {
                    "student_id": grade.student_id,
                    "student_name": grade.student_name,
                    "marks_obtained": grade.marks_obtained,
                    "percentage": grade.percentage,
                    "letter_grade": grade.letter_grade,
                    "is_passed": grade.is_passed,
                }
            )

        result_data = {
            "exam_id": exam.id,
            "exam_title": exam.title,
            "total_students": stats["total_students"],
            "appeared_students": stats["total_students"],
            "pass_percentage": (
                stats["passed_students"] / stats["total_students"] * 100
            )
            if stats["total_students"] > 0
            else 0,
            "average_marks": stats["average_marks"] or 0,
            "highest_marks": stats["highest_marks"] or 0,
            "lowest_marks": stats["lowest_marks"] or 0,
            "grade_distribution": grade_distribution,
            "student_results": student_results,
        }

        serializer = ExamResultsSerializer(result_data)
        return Response(serializer.data)


class GradeViewSet(viewsets.ModelViewSet):
    queryset = Grade.objects.all()
    serializer_class = GradeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = [
        "student_id",
        "course_id",
        "subject_id",
        "grade_type",
        "academic_year",
        "semester",
        "letter_grade",
        "is_passed",
    ]
    search_fields = ["student_name", "assessment_title", "course_name", "subject_name"]
    ordering_fields = ["graded_at", "marks_obtained", "percentage"]
    ordering = ["-graded_at"]

    @action(detail=False, methods=["post"])
    def bulk_grade(self, request):
        """Create multiple grades at once"""
        serializer = BulkGradeSerializer(data=request.data)
        if serializer.is_valid():
            grades_data = serializer.validated_data["grades"]
            grades = []

            with transaction.atomic():
                for grade_data in grades_data:
                    grade = Grade.objects.create(**grade_data)
                    grades.append(grade)

            response_serializer = GradeSerializer(grades, many=True)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"])
    def student_grades(self, request):
        """Get all grades for a specific student"""
        student_id = request.query_params.get("student_id")
        if not student_id:
            return Response(
                {"error": "student_id parameter required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        grades = self.queryset.filter(student_id=student_id)
        serializer = self.get_serializer(grades, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def course_grades(self, request):
        """Get all grades for a specific course"""
        course_id = request.query_params.get("course_id")
        if not course_id:
            return Response(
                {"error": "course_id parameter required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        grades = self.queryset.filter(course_id=course_id)
        serializer = self.get_serializer(grades, many=True)
        return Response(serializer.data)


class GradeScaleViewSet(viewsets.ModelViewSet):
    queryset = GradeScale.objects.all()
    serializer_class = GradeScaleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = [
        "course_id",
        "subject_id",
        "academic_year",
        "is_default",
        "is_active",
    ]
    search_fields = ["name", "description"]
    ordering = ["-created_at"]


class StudentResultViewSet(viewsets.ModelViewSet):
    queryset = StudentResult.objects.all()
    serializer_class = StudentResultSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = [
        "student_id",
        "course_id",
        "academic_year",
        "semester",
        "result_status",
        "is_promoted",
    ]
    search_fields = ["student_name", "course_name"]
    ordering_fields = ["generated_at", "semester_gpa", "overall_percentage"]
    ordering = ["-generated_at"]

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        """Publish student result"""
        result = self.get_object()
        if result.result_status == "DRAFT":
            result.result_status = "PUBLISHED"
            result.published_at = timezone.now()
            result.save()
            return Response({"message": "Result published successfully"})
        return Response(
            {"error": "Result is not in draft status"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=False, methods=["get"])
    def analytics(self, request):
        """Get assessment analytics"""
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        if not start_date or not end_date:
            return Response(
                {"error": "start_date and end_date parameters required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get analytics data
        assignments = Assignment.objects.filter(
            created_date__range=[start_date, end_date]
        )
        submissions = Submission.objects.filter(
            submitted_at__range=[start_date, end_date]
        )
        exams = Exam.objects.filter(exam_date__range=[start_date, end_date])

        analytics_data = {
            "period_start": start_date,
            "period_end": end_date,
            "total_assignments": assignments.count(),
            "total_submissions": submissions.count(),
            "total_exams": exams.count(),
            "average_assignment_score": submissions.aggregate(avg=Avg("percentage"))[
                "avg"
            ]
            or 0,
            "average_exam_score": Grade.objects.filter(
                grade_type="EXAM", graded_at__range=[start_date, end_date]
            ).aggregate(avg=Avg("percentage"))["avg"]
            or 0,
            "submission_trends": {},  # Could be populated with daily/weekly trends
            "grade_distribution": {},  # Could be populated with grade distribution
            "top_performers": [],  # Could be populated with top students
            "struggling_students": [],  # Could be populated with struggling students
        }

        serializer = AssessmentAnalyticsSerializer(analytics_data)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def gradebook(self, request):
        """Get gradebook for a course"""
        course_id = request.query_params.get("course_id")
        academic_year = request.query_params.get("academic_year")
        semester = request.query_params.get("semester")

        if not all([course_id, academic_year, semester]):
            return Response(
                {"error": "course_id, academic_year, and semester parameters required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get course information
        assignments = Assignment.objects.filter(
            course_id=course_id, academic_year=academic_year, semester=semester
        )

        exams = Exam.objects.filter(
            course_id=course_id, academic_year=academic_year, semester=semester
        )

        # Get all students with grades in this course
        grades = Grade.objects.filter(
            course_id=course_id, academic_year=academic_year, semester=semester
        )

        students = {}
        for grade in grades:
            if grade.student_id not in students:
                students[grade.student_id] = {
                    "student_id": grade.student_id,
                    "student_name": grade.student_name,
                    "student_email": grade.student_email,
                }

        # Build gradebook data structure
        gradebook_data = {
            "course_id": course_id,
            "course_name": assignments.first().course_name
            if assignments.exists()
            else "",
            "subject_id": assignments.first().subject_id
            if assignments.exists()
            else "",
            "subject_name": assignments.first().subject_name
            if assignments.exists()
            else "",
            "academic_year": academic_year,
            "semester": semester,
            "students": list(students.values()),
            "assessments": [],
            "grades_matrix": {},
        }

        # Add assessments
        for assignment in assignments:
            gradebook_data["assessments"].append(
                {
                    "id": str(assignment.id),
                    "title": assignment.title,
                    "type": "assignment",
                    "max_marks": assignment.max_marks,
                    "weightage": assignment.weightage,
                }
            )

        for exam in exams:
            gradebook_data["assessments"].append(
                {
                    "id": str(exam.id),
                    "title": exam.title,
                    "type": "exam",
                    "max_marks": exam.max_marks,
                    "weightage": exam.weightage,
                }
            )

        # Build grades matrix
        for student_id in students.keys():
            gradebook_data["grades_matrix"][student_id] = {}
            student_grades = grades.filter(student_id=student_id)

            for grade in student_grades:
                gradebook_data["grades_matrix"][student_id][grade.assessment_id] = {
                    "marks_obtained": grade.marks_obtained,
                    "percentage": grade.percentage,
                    "letter_grade": grade.letter_grade,
                    "is_passed": grade.is_passed,
                }

        serializer = GradebookSerializer(gradebook_data)
        return Response(serializer.data)
