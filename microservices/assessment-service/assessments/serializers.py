from django.utils import timezone
from rest_framework import serializers

from .models import (Assignment, Exam, Grade, GradeScale, StudentResult,
                     Submission)


class AssignmentSerializer(serializers.ModelSerializer):
    is_overdue = serializers.ReadOnlyField()
    days_until_due = serializers.ReadOnlyField()

    class Meta:
        model = Assignment
        fields = "__all__"
        read_only_fields = [
            "id",
            "submission_count",
            "average_grade",
            "completion_rate",
        ]

    def validate_due_date(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("Due date must be in the future.")
        return value

    def validate_passing_marks(self, value):
        max_marks = self.initial_data.get("max_marks", 100)
        if value > max_marks:
            raise serializers.ValidationError(
                "Passing marks cannot exceed maximum marks."
            )
        return value


class AssignmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = [
            "title",
            "description",
            "assignment_type",
            "course_id",
            "course_name",
            "subject_id",
            "subject_name",
            "academic_year",
            "semester",
            "instructions",
            "max_marks",
            "passing_marks",
            "weightage",
            "due_date",
            "late_submission_allowed",
            "late_penalty_per_day",
            "attachment",
            "reference_materials",
            "allow_multiple_submissions",
            "show_grades_immediately",
            "plagiarism_check_enabled",
            "created_by",
            "creator_name",
        ]


class SubmissionSerializer(serializers.ModelSerializer):
    assignment_title = serializers.CharField(source="assignment.title", read_only=True)
    assignment_max_marks = serializers.IntegerField(
        source="assignment.max_marks", read_only=True
    )

    class Meta:
        model = Submission
        fields = "__all__"
        read_only_fields = [
            "id",
            "is_late",
            "days_late",
            "percentage",
            "submitted_at",
            "last_modified",
            "attempt_number",
        ]

    def validate(self, data):
        assignment = data.get("assignment")
        student_id = data.get("student_id")

        # Check if assignment allows multiple submissions
        if assignment and not assignment.allow_multiple_submissions:
            existing_submission = Submission.objects.filter(
                assignment=assignment,
                student_id=student_id,
                status__in=["SUBMITTED", "GRADED"],
            ).exists()

            if existing_submission:
                raise serializers.ValidationError(
                    "Multiple submissions not allowed for this assignment."
                )

        # Check if assignment is still open
        if assignment and assignment.status == "CLOSED":
            raise serializers.ValidationError("Assignment is closed for submissions.")

        return data


class SubmissionGradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = ["marks_obtained", "grade", "teacher_feedback", "graded_by", "status"]

    def validate_marks_obtained(self, value):
        assignment = self.instance.assignment if self.instance else None
        if assignment and value > assignment.max_marks:
            raise serializers.ValidationError(
                f"Marks cannot exceed maximum marks ({assignment.max_marks})."
            )
        return value


class ExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exam
        fields = "__all__"
        read_only_fields = [
            "id",
            "total_students",
            "appeared_students",
            "passed_students",
            "average_marks",
            "highest_marks",
            "lowest_marks",
        ]

    def validate(self, data):
        exam_date = data.get("exam_date")
        end_time = data.get("end_time")

        if exam_date and end_time and exam_date >= end_time:
            raise serializers.ValidationError("End time must be after exam start time.")

        return data


class GradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grade
        fields = "__all__"
        read_only_fields = ["id", "percentage", "is_passed"]

    def validate_marks_obtained(self, value):
        max_marks = self.initial_data.get("max_marks")
        if max_marks and value > max_marks:
            raise serializers.ValidationError(
                "Marks obtained cannot exceed maximum marks."
            )
        return value


class GradeScaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradeScale
        fields = "__all__"
        read_only_fields = ["id"]


class StudentResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentResult
        fields = "__all__"
        read_only_fields = [
            "id",
            "generated_at",
            "updated_at",
            "overall_percentage",
            "overall_grade",
            "semester_gpa",
            "cumulative_gpa",
        ]


class AssignmentStatsSerializer(serializers.Serializer):
    total_assignments = serializers.IntegerField()
    published_assignments = serializers.IntegerField()
    overdue_assignments = serializers.IntegerField()
    total_submissions = serializers.IntegerField()
    pending_grading = serializers.IntegerField()
    average_completion_rate = serializers.DecimalField(max_digits=5, decimal_places=2)


class StudentPerformanceSerializer(serializers.Serializer):
    student_id = serializers.CharField()
    student_name = serializers.CharField()
    total_assignments = serializers.IntegerField()
    completed_assignments = serializers.IntegerField()
    pending_assignments = serializers.IntegerField()
    average_grade = serializers.DecimalField(max_digits=5, decimal_places=2)
    completion_rate = serializers.DecimalField(max_digits=5, decimal_places=2)


class CourseAssessmentSummarySerializer(serializers.Serializer):
    course_id = serializers.CharField()
    course_name = serializers.CharField()
    total_assignments = serializers.IntegerField()
    total_exams = serializers.IntegerField()
    total_students = serializers.IntegerField()
    average_performance = serializers.DecimalField(max_digits=5, decimal_places=2)
    completion_rate = serializers.DecimalField(max_digits=5, decimal_places=2)


class BulkGradeSerializer(serializers.Serializer):
    grades = serializers.ListField(child=serializers.DictField(), allow_empty=False)

    def validate_grades(self, value):
        required_fields = ["student_id", "marks_obtained", "assessment_id"]

        for grade_data in value:
            for field in required_fields:
                if field not in grade_data:
                    raise serializers.ValidationError(
                        f"Missing required field '{field}' in grade data."
                    )

        return value


class AssignmentBulkCreateSerializer(serializers.Serializer):
    assignments = serializers.ListField(
        child=AssignmentCreateSerializer(), allow_empty=False
    )

    def create(self, validated_data):
        assignments_data = validated_data["assignments"]
        assignments = []

        for assignment_data in assignments_data:
            assignment = Assignment.objects.create(**assignment_data)
            assignments.append(assignment)

        return assignments


class GradebookSerializer(serializers.Serializer):
    course_id = serializers.CharField()
    course_name = serializers.CharField()
    subject_id = serializers.CharField()
    subject_name = serializers.CharField()
    academic_year = serializers.CharField()
    semester = serializers.CharField()
    students = serializers.ListField(child=serializers.DictField())
    assessments = serializers.ListField(child=serializers.DictField())
    grades_matrix = serializers.DictField()  # student_id -> {assessment_id: grade_data}


class AssessmentAnalyticsSerializer(serializers.Serializer):
    period_start = serializers.DateTimeField()
    period_end = serializers.DateTimeField()
    total_assignments = serializers.IntegerField()
    total_submissions = serializers.IntegerField()
    total_exams = serializers.IntegerField()
    average_assignment_score = serializers.DecimalField(max_digits=5, decimal_places=2)
    average_exam_score = serializers.DecimalField(max_digits=5, decimal_places=2)
    submission_trends = serializers.DictField()
    grade_distribution = serializers.DictField()
    top_performers = serializers.ListField(child=serializers.DictField())
    struggling_students = serializers.ListField(child=serializers.DictField())


class ExamResultsSerializer(serializers.Serializer):
    exam_id = serializers.UUIDField()
    exam_title = serializers.CharField()
    total_students = serializers.IntegerField()
    appeared_students = serializers.IntegerField()
    pass_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
    average_marks = serializers.DecimalField(max_digits=5, decimal_places=2)
    highest_marks = serializers.DecimalField(max_digits=5, decimal_places=2)
    lowest_marks = serializers.DecimalField(max_digits=5, decimal_places=2)
    grade_distribution = serializers.DictField()
    student_results = serializers.ListField(child=serializers.DictField())
