import logging
from datetime import timedelta

import requests
from celery import shared_task
from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def send_assignment_notification(assignment_id, action):
    """Send notification when assignment is created, updated, or published"""
    from django.conf import settings

    from .models import Assignment

    try:
        assignment = Assignment.objects.get(id=assignment_id)

        notification_data = {
            "recipient_type": "STUDENT",
            "recipient_ids": [],  # Will be populated by notification service
            "title": f"Assignment {action.title()}: {assignment.title}",
            "message": f'Assignment "{assignment.title}" has been {action.lower()}.',
            "notification_type": "ASSIGNMENT",
            "priority": "MEDIUM",
            "metadata": {
                "assignment_id": str(assignment.id),
                "course_id": assignment.course_id,
                "subject_id": assignment.subject_id,
                "due_date": assignment.due_date.isoformat(),
                "action": action,
            },
        }

        # Send to notification service
        response = requests.post(
            f"{settings.NOTIFICATION_SERVICE_URL}/api/v1/notifications/notifications/",
            json=notification_data,
            timeout=10,
        )

        if response.status_code == 201:
            logger.info(
                f"Assignment notification sent successfully for {assignment_id}"
            )
        else:
            logger.error(f"Failed to send assignment notification: {response.text}")

    except Assignment.DoesNotExist:
        logger.error(f"Assignment {assignment_id} not found")
    except Exception as e:
        logger.error(f"Error sending assignment notification: {str(e)}")


@shared_task
def process_grade_calculation(student_id, course_id):
    """Calculate and update student grades and results"""
    from .models import Grade, StudentResult

    try:
        # Get all grades for the student in the course
        grades = Grade.objects.filter(student_id=student_id, course_id=course_id)

        if not grades.exists():
            return

        # Group by academic year and semester
        academic_periods = grades.values("academic_year", "semester").distinct()

        for period in academic_periods:
            academic_year = period["academic_year"]
            semester = period["semester"]

            period_grades = grades.filter(
                academic_year=academic_year, semester=semester
            )

            # Calculate weighted average
            total_weightage = (
                period_grades.aggregate(total=Sum("weightage"))["total"] or 0
            )

            if total_weightage > 0:
                weighted_sum = sum(
                    (grade.percentage * grade.weightage / 100)
                    for grade in period_grades
                )
                overall_percentage = (weighted_sum / total_weightage) * 100
            else:
                overall_percentage = (
                    period_grades.aggregate(avg=Avg("percentage"))["avg"] or 0
                )

            # Calculate GPA
            gpa = period_grades.aggregate(avg=Avg("grade_points"))["avg"] or 0

            # Update or create student result
            result, created = StudentResult.objects.update_or_create(
                student_id=student_id,
                course_id=course_id,
                academic_year=academic_year,
                semester=semester,
                defaults={
                    "student_name": period_grades.first().student_name,
                    "student_email": period_grades.first().student_email,
                    "course_name": period_grades.first().course_name,
                    "total_subjects": period_grades.values("subject_id")
                    .distinct()
                    .count(),
                    "subjects_passed": period_grades.filter(is_passed=True)
                    .values("subject_id")
                    .distinct()
                    .count(),
                    "subjects_failed": period_grades.filter(is_passed=False)
                    .values("subject_id")
                    .distinct()
                    .count(),
                    "semester_gpa": gpa,
                    "overall_percentage": overall_percentage,
                    "overall_grade": _calculate_letter_grade(overall_percentage),
                    "is_promoted": overall_percentage >= 40,
                    "generated_by": "system",
                    "subject_results": _build_subject_results(period_grades),
                },
            )

            logger.info(
                f"Updated result for student {student_id} in {course_id} {academic_year} {semester}"
            )

    except Exception as e:
        logger.error(f"Error calculating grades for student {student_id}: {str(e)}")


def _calculate_letter_grade(percentage):
    """Calculate letter grade from percentage"""
    if percentage >= 90:
        return "A+"
    elif percentage >= 80:
        return "A"
    elif percentage >= 70:
        return "B+"
    elif percentage >= 60:
        return "B"
    elif percentage >= 50:
        return "C+"
    elif percentage >= 40:
        return "C"
    else:
        return "F"


def _build_subject_results(grades):
    """Build detailed subject results"""
    subjects = {}

    for grade in grades:
        subject_id = grade.subject_id
        if subject_id not in subjects:
            subjects[subject_id] = {
                "subject_name": grade.subject_name,
                "assessments": [],
                "total_marks": 0,
                "obtained_marks": 0,
                "percentage": 0,
                "grade": "",
                "is_passed": False,
            }

        subjects[subject_id]["assessments"].append(
            {
                "assessment_title": grade.assessment_title,
                "assessment_type": grade.grade_type,
                "marks_obtained": float(grade.marks_obtained),
                "max_marks": float(grade.max_marks),
                "percentage": float(grade.percentage),
                "grade": grade.letter_grade,
            }
        )

    # Calculate subject-wise totals
    for subject_id, subject_data in subjects.items():
        subject_grades = grades.filter(subject_id=subject_id)
        subject_data["total_marks"] = (
            subject_grades.aggregate(total=Sum("max_marks"))["total"] or 0
        )
        subject_data["obtained_marks"] = (
            subject_grades.aggregate(total=Sum("marks_obtained"))["total"] or 0
        )

        if subject_data["total_marks"] > 0:
            subject_data["percentage"] = (
                subject_data["obtained_marks"] / subject_data["total_marks"]
            ) * 100

        subject_data["grade"] = _calculate_letter_grade(subject_data["percentage"])
        subject_data["is_passed"] = subject_data["percentage"] >= 40

    return subjects


@shared_task
def process_overdue_assignments():
    """Process overdue assignments and send notifications"""
    from .models import Assignment

    try:
        overdue_assignments = Assignment.objects.filter(
            due_date__lt=timezone.now(), status="PUBLISHED"
        )

        for assignment in overdue_assignments:
            # Update assignment status
            assignment.status = "CLOSED"
            assignment.save()

            # Send overdue notification
            send_assignment_notification.delay(assignment.id, "OVERDUE")

        logger.info(f"Processed {overdue_assignments.count()} overdue assignments")

    except Exception as e:
        logger.error(f"Error processing overdue assignments: {str(e)}")


@shared_task
def send_assignment_reminders():
    """Send reminders for upcoming assignment due dates"""
    from django.conf import settings

    from .models import Assignment

    try:
        # Get assignments due in next 24 hours
        tomorrow = timezone.now() + timedelta(days=1)
        upcoming_assignments = Assignment.objects.filter(
            due_date__lte=tomorrow, due_date__gt=timezone.now(), status="PUBLISHED"
        )

        for assignment in upcoming_assignments:
            notification_data = {
                "recipient_type": "STUDENT",
                "recipient_ids": [],
                "title": f"Assignment Due Tomorrow: {assignment.title}",
                "message": f'Reminder: Assignment "{assignment.title}" is due tomorrow at {assignment.due_date.strftime("%H:%M")}.',
                "notification_type": "REMINDER",
                "priority": "HIGH",
                "metadata": {
                    "assignment_id": str(assignment.id),
                    "course_id": assignment.course_id,
                    "due_date": assignment.due_date.isoformat(),
                },
            }

            requests.post(
                f"{settings.NOTIFICATION_SERVICE_URL}/api/v1/notifications/notifications/",
                json=notification_data,
                timeout=10,
            )

        logger.info(f"Sent reminders for {upcoming_assignments.count()} assignments")

    except Exception as e:
        logger.error(f"Error sending assignment reminders: {str(e)}")


@shared_task
def generate_grade_reports():
    """Generate weekly grade reports"""
    from django.conf import settings

    from .models import Grade, StudentResult

    try:
        # Get grades from the past week
        week_ago = timezone.now() - timedelta(days=7)
        recent_grades = Grade.objects.filter(graded_at__gte=week_ago)

        if not recent_grades.exists():
            logger.info("No grades to report this week")
            return

        # Group by course
        courses = recent_grades.values("course_id", "course_name").distinct()

        for course in courses:
            course_grades = recent_grades.filter(course_id=course["course_id"])

            report_data = {
                "course_id": course["course_id"],
                "course_name": course["course_name"],
                "period_start": week_ago.isoformat(),
                "period_end": timezone.now().isoformat(),
                "total_grades": course_grades.count(),
                "average_grade": course_grades.aggregate(avg=Avg("percentage"))["avg"]
                or 0,
                "grade_distribution": {},
            }

            # Calculate grade distribution
            for grade_letter in ["A+", "A", "B+", "B", "C+", "C", "D", "F"]:
                count = course_grades.filter(letter_grade=grade_letter).count()
                if count > 0:
                    report_data["grade_distribution"][grade_letter] = count

            # Send report to notification service
            notification_data = {
                "recipient_type": "STAFF",
                "recipient_ids": [],
                "title": f'Weekly Grade Report: {course["course_name"]}',
                "message": f'Grade report for {course["course_name"]} - {course_grades.count()} new grades this week.',
                "notification_type": "REPORT",
                "priority": "LOW",
                "metadata": report_data,
            }

            requests.post(
                f"{settings.NOTIFICATION_SERVICE_URL}/api/v1/notifications/notifications/",
                json=notification_data,
                timeout=10,
            )

        logger.info(f"Generated grade reports for {courses.count()} courses")

    except Exception as e:
        logger.error(f"Error generating grade reports: {str(e)}")


@shared_task
def cleanup_old_submissions():
    """Clean up old draft submissions and temporary files"""
    from .models import Submission

    try:
        # Delete draft submissions older than 30 days
        month_ago = timezone.now() - timedelta(days=30)
        old_drafts = Submission.objects.filter(
            status="DRAFT", submitted_at__lt=month_ago
        )

        count = old_drafts.count()
        old_drafts.delete()

        logger.info(f"Cleaned up {count} old draft submissions")

    except Exception as e:
        logger.error(f"Error cleaning up old submissions: {str(e)}")


@shared_task
def sync_user_data():
    """Sync user data from User Management Service"""
    from django.conf import settings

    try:
        # Get updated user information
        response = requests.get(
            f"{settings.USER_MANAGEMENT_SERVICE_URL}/api/v1/users/users/", timeout=30
        )

        if response.status_code == 200:
            users = response.json().get("results", [])

            # Update user information in grades and submissions
            for user in users:
                user_id = user.get("id")
                user_name = (
                    f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                )
                user_email = user.get("email", "")

                if user_id:
                    # Update submissions
                    from .models import Submission

                    Submission.objects.filter(student_id=user_id).update(
                        student_name=user_name, student_email=user_email
                    )

                    # Update grades
                    from .models import Grade

                    Grade.objects.filter(student_id=user_id).update(
                        student_name=user_name, student_email=user_email
                    )

            logger.info(f"Synced data for {len(users)} users")
        else:
            logger.error(f"Failed to sync user data: {response.text}")

    except Exception as e:
        logger.error(f"Error syncing user data: {str(e)}")


@shared_task
def calculate_class_rankings():
    """Calculate class rankings based on GPA and performance"""
    from .models import StudentResult

    try:
        # Group by course and academic period
        academic_periods = StudentResult.objects.values(
            "course_id", "academic_year", "semester"
        ).distinct()

        for period in academic_periods:
            results = StudentResult.objects.filter(
                course_id=period["course_id"],
                academic_year=period["academic_year"],
                semester=period["semester"],
                result_status="PUBLISHED",
            ).order_by("-semester_gpa", "-overall_percentage")

            # Update rankings
            for rank, result in enumerate(results, 1):
                result.class_rank = rank
                result.save(update_fields=["class_rank"])

        logger.info("Updated class rankings")

    except Exception as e:
        logger.error(f"Error calculating class rankings: {str(e)}")


@shared_task
def send_grade_notifications(grade_id):
    """Send notification when a grade is published"""
    from django.conf import settings

    from .models import Grade

    try:
        grade = Grade.objects.get(id=grade_id)

        notification_data = {
            "recipient_type": "STUDENT",
            "recipient_ids": [grade.student_id],
            "title": f"Grade Published: {grade.assessment_title}",
            "message": f'Your grade for "{grade.assessment_title}" has been published. Grade: {grade.letter_grade} ({grade.percentage}%)',
            "notification_type": "GRADE",
            "priority": "MEDIUM",
            "metadata": {
                "grade_id": str(grade.id),
                "assessment_title": grade.assessment_title,
                "grade": grade.letter_grade,
                "percentage": float(grade.percentage),
                "course_name": grade.course_name,
            },
        }

        response = requests.post(
            f"{settings.NOTIFICATION_SERVICE_URL}/api/v1/notifications/notifications/",
            json=notification_data,
            timeout=10,
        )

        if response.status_code == 201:
            logger.info(f"Grade notification sent for {grade_id}")
        else:
            logger.error(f"Failed to send grade notification: {response.text}")

    except Grade.DoesNotExist:
        logger.error(f"Grade {grade_id} not found")
    except Exception as e:
        logger.error(f"Error sending grade notification: {str(e)}")


@shared_task
def auto_grade_assignments():
    """Auto-grade assignments that support automatic grading"""
    from .models import Assignment, Submission

    try:
        # Get assignments with auto-grading enabled
        auto_grade_assignments = Assignment.objects.filter(
            status="PUBLISHED"
            # Add more criteria for auto-gradable assignments
        )

        for assignment in auto_grade_assignments:
            ungraded_submissions = assignment.submissions.filter(
                status="SUBMITTED", marks_obtained__isnull=True
            )

            for submission in ungraded_submissions:
                # Simple auto-grading logic (can be enhanced)
                if submission.submission_text:
                    word_count = len(submission.submission_text.split())
                    submission.word_count = word_count

                    # Basic scoring based on word count (example)
                    if word_count >= 500:
                        submission.marks_obtained = assignment.max_marks * 0.9
                    elif word_count >= 300:
                        submission.marks_obtained = assignment.max_marks * 0.7
                    elif word_count >= 100:
                        submission.marks_obtained = assignment.max_marks * 0.5
                    else:
                        submission.marks_obtained = assignment.max_marks * 0.3

                    submission.status = "GRADED"
                    submission.graded_at = timezone.now()
                    submission.graded_by = "auto_grader"
                    submission.teacher_feedback = (
                        "Auto-graded based on submission criteria."
                    )
                    submission.save()

                    # Send grade notification
                    send_grade_notifications.delay(submission.id)

        logger.info("Auto-grading completed")

    except Exception as e:
        logger.error(f"Error in auto-grading: {str(e)}")
