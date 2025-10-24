from django.contrib import admin
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import (Assignment, Exam, Grade, GradeScale, StudentResult,
                     Submission)


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "assignment_type",
        "course_name",
        "subject_name",
        "status",
        "due_date",
        "max_marks",
        "submission_count",
        "creator_name",
    ]
    list_filter = [
        "assignment_type",
        "status",
        "course_id",
        "subject_id",
        "academic_year",
        "semester",
        "late_submission_allowed",
    ]
    search_fields = [
        "title",
        "description",
        "course_name",
        "subject_name",
        "creator_name",
    ]
    ordering = ["-created_date"]
    readonly_fields = [
        "id",
        "created_date",
        "submission_count",
        "average_grade",
        "completion_rate",
    ]

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("title", "description", "assignment_type", "status")},
        ),
        (
            "Academic Context",
            {
                "fields": (
                    "course_id",
                    "course_name",
                    "subject_id",
                    "subject_name",
                    "academic_year",
                    "semester",
                )
            },
        ),
        (
            "Assignment Details",
            {
                "fields": (
                    "instructions",
                    "max_marks",
                    "passing_marks",
                    "weightage",
                    "attachment",
                    "reference_materials",
                )
            },
        ),
        (
            "Timing & Submission",
            {
                "fields": (
                    "due_date",
                    "late_submission_allowed",
                    "late_penalty_per_day",
                    "allow_multiple_submissions",
                )
            },
        ),
        (
            "Settings",
            {"fields": ("show_grades_immediately", "plagiarism_check_enabled")},
        ),
        ("Creator Information", {"fields": ("created_by", "creator_name")}),
        (
            "Statistics",
            {
                "fields": ("submission_count", "average_grade", "completion_rate"),
                "classes": ("collapse",),
            },
        ),
        ("Metadata", {"fields": ("id", "created_date"), "classes": ("collapse",)}),
    )

    actions = ["publish_assignments", "close_assignments", "mark_as_graded"]

    def publish_assignments(self, request, queryset):
        updated = queryset.filter(status="DRAFT").update(status="PUBLISHED")
        self.message_user(request, f"{updated} assignments published.")

    publish_assignments.short_description = "Publish selected assignments"

    def close_assignments(self, request, queryset):
        updated = queryset.filter(status="PUBLISHED").update(status="CLOSED")
        self.message_user(request, f"{updated} assignments closed.")

    close_assignments.short_description = "Close selected assignments"

    def mark_as_graded(self, request, queryset):
        updated = queryset.update(status="GRADED")
        self.message_user(request, f"{updated} assignments marked as graded.")

    mark_as_graded.short_description = "Mark selected assignments as graded"


class SubmissionInline(admin.TabularInline):
    model = Submission
    extra = 0
    readonly_fields = ["submitted_at", "is_late", "days_late", "percentage"]
    fields = [
        "student_name",
        "status",
        "marks_obtained",
        "grade",
        "is_late",
        "submitted_at",
    ]


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = [
        "assignment_title",
        "student_name",
        "status",
        "marks_obtained",
        "percentage",
        "is_late",
        "submitted_at",
    ]
    list_filter = [
        "status",
        "is_late",
        "assignment__course_id",
        "assignment__subject_id",
        "assignment__academic_year",
        "submitted_at",
    ]
    search_fields = [
        "student_name",
        "student_email",
        "assignment__title",
        "submission_text",
    ]
    ordering = ["-submitted_at"]
    readonly_fields = [
        "id",
        "submitted_at",
        "last_modified",
        "is_late",
        "days_late",
        "percentage",
        "attempt_number",
    ]

    fieldsets = (
        ("Assignment Information", {"fields": ("assignment",)}),
        (
            "Student Information",
            {"fields": ("student_id", "student_name", "student_email")},
        ),
        (
            "Submission Content",
            {"fields": ("submission_text", "attachment", "additional_files")},
        ),
        (
            "Grading",
            {
                "fields": (
                    "status",
                    "marks_obtained",
                    "grade",
                    "percentage",
                    "teacher_feedback",
                    "graded_by",
                    "graded_at",
                )
            },
        ),
        (
            "Submission Details",
            {
                "fields": (
                    "submitted_at",
                    "last_modified",
                    "is_late",
                    "days_late",
                    "attempt_number",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Quality Checks",
            {"fields": ("plagiarism_score", "word_count"), "classes": ("collapse",)},
        ),
        ("Metadata", {"fields": ("id", "ip_address"), "classes": ("collapse",)}),
    )

    def assignment_title(self, obj):
        return obj.assignment.title

    assignment_title.short_description = "Assignment"

    actions = ["grade_submissions", "mark_as_graded"]

    def grade_submissions(self, request, queryset):
        # This would open a form to bulk grade submissions
        # For now, just mark as graded
        updated = queryset.filter(status="SUBMITTED").update(
            status="GRADED", graded_at=timezone.now()
        )
        self.message_user(request, f"{updated} submissions marked as graded.")

    grade_submissions.short_description = "Grade selected submissions"


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "exam_type",
        "course_name",
        "subject_name",
        "exam_date",
        "status",
        "max_marks",
        "appeared_students",
        "creator_name",
    ]
    list_filter = [
        "exam_type",
        "status",
        "course_id",
        "subject_id",
        "academic_year",
        "semester",
        "exam_date",
    ]
    search_fields = ["title", "description", "course_name", "subject_name", "venue"]
    ordering = ["exam_date"]
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "total_students",
        "appeared_students",
        "passed_students",
        "average_marks",
        "highest_marks",
        "lowest_marks",
    ]

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("title", "description", "exam_type", "status")},
        ),
        (
            "Academic Context",
            {
                "fields": (
                    "course_id",
                    "course_name",
                    "subject_id",
                    "subject_name",
                    "academic_year",
                    "semester",
                )
            },
        ),
        (
            "Exam Details",
            {
                "fields": (
                    "max_marks",
                    "passing_marks",
                    "duration_minutes",
                    "weightage",
                    "instructions",
                    "materials_allowed",
                )
            },
        ),
        ("Scheduling", {"fields": ("exam_date", "end_time", "venue", "invigilator")}),
        (
            "Results Statistics",
            {
                "fields": (
                    "total_students",
                    "appeared_students",
                    "passed_students",
                    "average_marks",
                    "highest_marks",
                    "lowest_marks",
                ),
                "classes": ("collapse",),
            },
        ),
        ("Creator Information", {"fields": ("created_by", "creator_name")}),
        (
            "Metadata",
            {"fields": ("id", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    actions = ["start_exams", "complete_exams", "cancel_exams"]

    def start_exams(self, request, queryset):
        updated = queryset.filter(status="SCHEDULED").update(status="ONGOING")
        self.message_user(request, f"{updated} exams started.")

    start_exams.short_description = "Start selected exams"

    def complete_exams(self, request, queryset):
        updated = queryset.filter(status="ONGOING").update(status="COMPLETED")
        self.message_user(request, f"{updated} exams completed.")

    complete_exams.short_description = "Complete selected exams"

    def cancel_exams(self, request, queryset):
        updated = queryset.update(status="CANCELLED")
        self.message_user(request, f"{updated} exams cancelled.")

    cancel_exams.short_description = "Cancel selected exams"


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = [
        "student_name",
        "assessment_title",
        "course_name",
        "subject_name",
        "grade_type",
        "marks_obtained",
        "max_marks",
        "letter_grade",
        "is_passed",
    ]
    list_filter = [
        "grade_type",
        "letter_grade",
        "is_passed",
        "course_id",
        "subject_id",
        "academic_year",
        "semester",
        "graded_at",
    ]
    search_fields = [
        "student_name",
        "student_email",
        "assessment_title",
        "course_name",
        "subject_name",
    ]
    ordering = ["-graded_at"]
    readonly_fields = ["id", "percentage", "is_passed", "created_at", "updated_at"]

    fieldsets = (
        (
            "Student Information",
            {"fields": ("student_id", "student_name", "student_email")},
        ),
        (
            "Academic Context",
            {
                "fields": (
                    "course_id",
                    "course_name",
                    "subject_id",
                    "subject_name",
                    "academic_year",
                    "semester",
                )
            },
        ),
        (
            "Assessment Information",
            {"fields": ("grade_type", "assessment_id", "assessment_title")},
        ),
        (
            "Grading",
            {
                "fields": (
                    "marks_obtained",
                    "max_marks",
                    "percentage",
                    "letter_grade",
                    "grade_points",
                    "is_passed",
                )
            },
        ),
        ("Feedback", {"fields": ("remarks", "teacher_feedback")}),
        ("Grader Information", {"fields": ("graded_by", "grader_name", "graded_at")}),
        (
            "Metadata",
            {
                "fields": (
                    "id",
                    "weightage",
                    "is_final_grade",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    actions = ["mark_as_passed", "mark_as_failed"]

    def mark_as_passed(self, request, queryset):
        updated = queryset.update(is_passed=True)
        self.message_user(request, f"{updated} grades marked as passed.")

    mark_as_passed.short_description = "Mark selected grades as passed"

    def mark_as_failed(self, request, queryset):
        updated = queryset.update(is_passed=False)
        self.message_user(request, f"{updated} grades marked as failed.")

    mark_as_failed.short_description = "Mark selected grades as failed"


@admin.register(GradeScale)
class GradeScaleAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "course_id",
        "subject_id",
        "academic_year",
        "is_default",
        "is_active",
    ]
    list_filter = ["is_default", "is_active", "course_id", "academic_year"]
    search_fields = ["name", "description", "course_id", "subject_id"]
    ordering = ["-created_at"]
    readonly_fields = ["id", "created_at", "updated_at"]

    fieldsets = (
        ("Basic Information", {"fields": ("name", "description")}),
        (
            "Academic Context",
            {"fields": ("course_id", "subject_id", "academic_year", "semester")},
        ),
        ("Scale Configuration", {"fields": ("scale_data", "is_default", "is_active")}),
        (
            "Metadata",
            {
                "fields": ("id", "created_by", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(StudentResult)
class StudentResultAdmin(admin.ModelAdmin):
    list_display = [
        "student_name",
        "course_name",
        "academic_year",
        "semester",
        "semester_gpa",
        "overall_percentage",
        "overall_grade",
        "result_status",
        "is_promoted",
    ]
    list_filter = [
        "result_status",
        "is_promoted",
        "course_id",
        "academic_year",
        "semester",
        "overall_grade",
    ]
    search_fields = ["student_name", "student_email", "course_name"]
    ordering = ["-generated_at"]
    readonly_fields = [
        "id",
        "generated_at",
        "updated_at",
        "overall_percentage",
        "overall_grade",
        "semester_gpa",
        "cumulative_gpa",
    ]

    fieldsets = (
        (
            "Student Information",
            {"fields": ("student_id", "student_name", "student_email")},
        ),
        (
            "Academic Context",
            {"fields": ("course_id", "course_name", "academic_year", "semester")},
        ),
        (
            "Results Summary",
            {"fields": ("total_subjects", "subjects_passed", "subjects_failed")},
        ),
        (
            "GPA & Performance",
            {
                "fields": (
                    "total_credits",
                    "earned_credits",
                    "semester_gpa",
                    "cumulative_gpa",
                    "overall_percentage",
                    "overall_grade",
                )
            },
        ),
        (
            "Status & Ranking",
            {"fields": ("result_status", "is_promoted", "class_rank", "remarks")},
        ),
        (
            "Detailed Results",
            {"fields": ("subject_results",), "classes": ("collapse",)},
        ),
        (
            "Metadata",
            {
                "fields": (
                    "id",
                    "generated_by",
                    "generated_at",
                    "published_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    actions = ["publish_results", "withhold_results", "promote_students"]

    def publish_results(self, request, queryset):
        updated = queryset.filter(result_status="DRAFT").update(
            result_status="PUBLISHED", published_at=timezone.now()
        )
        self.message_user(request, f"{updated} results published.")

    publish_results.short_description = "Publish selected results"

    def withhold_results(self, request, queryset):
        updated = queryset.update(result_status="WITHHELD")
        self.message_user(request, f"{updated} results withheld.")

    withhold_results.short_description = "Withhold selected results"

    def promote_students(self, request, queryset):
        updated = queryset.filter(overall_percentage__gte=40).update(is_promoted=True)
        self.message_user(request, f"{updated} students promoted.")

    promote_students.short_description = "Promote eligible students"


# Custom admin site configuration
admin.site.site_header = "Assessment Management Administration"
admin.site.site_title = "Assessment Management Admin"
admin.site.index_title = "Welcome to Assessment Management Administration"
