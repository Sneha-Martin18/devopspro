import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import serializers
from django.core.files.storage import \
    FileSystemStorage  # To upload Profile Picture
from django.core.mail import send_mail
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt, csrf_protect

from student_management_app.models import (Assignment, AssignmentSubmission,
                                           Attendance, AttendanceReport,
                                           Courses, CustomUser, FeedBackStaffs,
                                           Fine, LeaveReportStaff,
                                           SessionYearModel, Staffs,
                                           StudentResult, Students, Subjects)

from .forms import AddFineForm


@login_required
@csrf_protect
def staff_grade_assignment(request, submission_id):
    from student_management_app.models import AssignmentSubmission

    try:
        submission = AssignmentSubmission.objects.get(id=submission_id)
    except AssignmentSubmission.DoesNotExist:
        messages.error(request, "Submission not found")
        return redirect(
            "staff_view_submissions", assignment_id=submission.assignment_id.id
        )

    if request.method == "POST":
        marks = request.POST.get("marks")
        try:
            marks = float(marks)
            if marks < 1 or marks > 10:
                messages.error(request, "Grade must be between 1 and 10.")
                return redirect("staff_grade_assignment", submission_id=submission_id)
        except (ValueError, TypeError):
            messages.error(request, "Invalid grade value")
            return redirect("staff_grade_assignment", submission_id=submission_id)

        # Check permission
        if submission.assignment_id.subject_id.staff_id != request.user:
            messages.error(
                request, "You don't have permission to grade this submission"
            )
            return redirect(
                "staff_view_submissions", assignment_id=submission.assignment_id.id
            )

        submission.marks = marks
        submission.status = "graded"
        submission.save()
        messages.success(request, "Grade updated successfully!")
        return redirect(
            "staff_view_submissions", assignment_id=submission.assignment_id.id
        )

    context = {"submission": submission, "page_title": "Grade Assignment Submission"}
    return render(request, "staff_template/grade_assignment.html", context)


def staff_home(request):
    try:
        staff = Staffs.objects.get(admin=request.user)
    except Staffs.DoesNotExist:
        messages.error(
            request, "Staff profile not found. Please contact administrator."
        )
        return redirect("login")

    # Fetching All Students under Staff

    subjects = Subjects.objects.filter(staff_id=request.user.id)
    course_id_list = []
    for subject in subjects:
        course = Courses.objects.get(id=subject.course_id.id)
        course_id_list.append(course.id)

    final_course = []
    # Removing Duplicate Course Id
    for course_id in course_id_list:
        if course_id not in final_course:
            final_course.append(course_id)

    students_count = Students.objects.filter(course_id__in=final_course).count()
    subject_count = subjects.count()

    # Fetch All Attendance Count
    attendance_count = Attendance.objects.filter(subject_id__in=subjects).count()
    # Fetch All Approve Leave
    staff = Staffs.objects.get(admin=request.user.id)
    leave_count = LeaveReportStaff.objects.filter(
        staff_id=staff.id, leave_status=1
    ).count()

    # Fetch Attendance Data by Subjects
    subject_list = []
    attendance_list = []
    for subject in subjects:
        attendance_count1 = Attendance.objects.filter(subject_id=subject.id).count()
        subject_list.append(subject.subject_name)
        attendance_list.append(attendance_count1)

    students_attendance = Students.objects.filter(course_id__in=final_course)
    student_list = []
    student_list_attendance_present = []
    student_list_attendance_absent = []
    for student in students_attendance:
        attendance_present_count = AttendanceReport.objects.filter(
            status=True, student_id=student.id
        ).count()
        attendance_absent_count = AttendanceReport.objects.filter(
            status=False, student_id=student.id
        ).count()
        student_list.append(student.admin.first_name + " " + student.admin.last_name)
        student_list_attendance_present.append(attendance_present_count)
        student_list_attendance_absent.append(attendance_absent_count)

    context = {
        "students_count": students_count,
        "attendance_count": attendance_count,
        "leave_count": leave_count,
        "subject_count": subject_count,
        "subject_list": subject_list,
        "attendance_list": attendance_list,
        "student_list": student_list,
        "attendance_present_list": student_list_attendance_present,
        "attendance_absent_list": student_list_attendance_absent,
    }
    return render(request, "staff_template/staff_home_template.html", context)


def staff_take_attendance(request):
    subjects = Subjects.objects.filter(staff_id=request.user.id)
    session_years = SessionYearModel.objects.all()
    context = {"subjects": subjects, "session_years": session_years}
    return render(request, "staff_template/take_attendance_template.html", context)


def staff_apply_leave(request):
    staff_obj = Staffs.objects.get(admin=request.user.id)
    leave_data = LeaveReportStaff.objects.filter(staff_id=staff_obj)
    context = {"leave_data": leave_data}
    return render(request, "staff_template/staff_apply_leave_template.html", context)


def staff_apply_leave_save(request):
    if request.method != "POST":
        messages.error(request, "Invalid Method")
        return redirect("staff_apply_leave")
    else:
        leave_date = request.POST.get("leave_date")
        leave_message = request.POST.get("leave_message")

        staff_obj = Staffs.objects.get(admin=request.user.id)
        try:
            leave_report = LeaveReportStaff(
                staff_id=staff_obj,
                leave_date=leave_date,
                leave_message=leave_message,
                leave_status=0,
            )
            leave_report.save()
            messages.success(request, "Applied for Leave.")
            return redirect("staff_apply_leave")
        except:
            messages.error(request, "Failed to Apply Leave")
            return redirect("staff_apply_leave")


def staff_feedback(request):
    staff_obj = Staffs.objects.get(admin=request.user.id)
    feedback_data = FeedBackStaffs.objects.filter(staff_id=staff_obj)
    context = {"feedback_data": feedback_data}
    return render(request, "staff_template/staff_feedback_template.html", context)


def staff_feedback_save(request):
    if request.method != "POST":
        messages.error(request, "Invalid Method.")
        return redirect("staff_feedback")
    else:
        feedback = request.POST.get("feedback_message")
        staff_obj = Staffs.objects.get(admin=request.user.id)

        try:
            add_feedback = FeedBackStaffs(
                staff_id=staff_obj, feedback=feedback, feedback_reply=""
            )
            add_feedback.save()
            messages.success(request, "Feedback Sent.")
            return redirect("staff_feedback")
        except:
            messages.error(request, "Failed to Send Feedback.")
            return redirect("staff_feedback")


# WE don't need csrf_token when using Ajax
@csrf_exempt
def get_students(request):
    # Getting Values from Ajax POST 'Fetch Student'
    subject_id = request.POST.get("subject")
    session_year = request.POST.get("session_year")

    # Students enroll to Course, Course has Subjects
    # Getting all data from subject model based on subject_id
    subject_model = Subjects.objects.get(id=subject_id)

    session_model = SessionYearModel.objects.get(id=session_year)

    students = Students.objects.filter(
        course_id=subject_model.course_id, session_year_id=session_model
    )

    # Only Passing Student Id and Student Name Only
    list_data = []

    for student in students:
        data_small = {
            "id": student.admin.id,
            "name": student.admin.first_name + " " + student.admin.last_name,
        }
        list_data.append(data_small)

    return JsonResponse(
        json.dumps(list_data), content_type="application/json", safe=False
    )


@csrf_exempt
def save_attendance_data(request):
    # Get Values from Staf Take Attendance form via AJAX (JavaScript)
    # Use getlist to access HTML Array/List Input Data
    student_ids = request.POST.get("student_ids")
    subject_id = request.POST.get("subject_id")
    attendance_date = request.POST.get("attendance_date")
    session_year_id = request.POST.get("session_year_id")

    subject_model = Subjects.objects.get(id=subject_id)
    session_year_model = SessionYearModel.objects.get(id=session_year_id)

    json_student = json.loads(student_ids)
    # print(dict_student[0]['id'])

    # print(student_ids)
    try:
        # First Attendance Data is Saved on Attendance Model
        attendance = Attendance(
            subject_id=subject_model,
            attendance_date=attendance_date,
            session_year_id=session_year_model,
        )
        attendance.save()

        for stud in json_student:
            # Attendance of Individual Student saved on AttendanceReport Model
            student = Students.objects.get(admin=stud["id"])
            attendance_report = AttendanceReport(
                student_id=student, attendance_id=attendance, status=stud["status"]
            )
            attendance_report.save()
        return HttpResponse("OK")
    except:
        return HttpResponse("Error")


def staff_update_attendance(request):
    subjects = Subjects.objects.filter(staff_id=request.user.id)
    session_years = SessionYearModel.objects.all()
    context = {"subjects": subjects, "session_years": session_years}
    return render(request, "staff_template/update_attendance_template.html", context)


@csrf_exempt
def get_attendance_dates(request):
    # Getting Values from Ajax POST 'Fetch Student'
    subject_id = request.POST.get("subject")
    session_year = request.POST.get("session_year_id")

    # Students enroll to Course, Course has Subjects
    # Getting all data from subject model based on subject_id
    subject_model = Subjects.objects.get(id=subject_id)

    session_model = SessionYearModel.objects.get(id=session_year)

    # students = Students.objects.filter(course_id=subject_model.course_id, session_year_id=session_model)
    attendance = Attendance.objects.filter(
        subject_id=subject_model, session_year_id=session_model
    )

    # Only Passing Student Id and Student Name Only
    list_data = []

    for attendance_single in attendance:
        data_small = {
            "id": attendance_single.id,
            "attendance_date": str(attendance_single.attendance_date),
            "session_year_id": attendance_single.session_year_id.id,
        }
        list_data.append(data_small)

    return JsonResponse(
        json.dumps(list_data), content_type="application/json", safe=False
    )


@csrf_exempt
def get_attendance_student(request):
    # Getting Values from Ajax POST 'Fetch Student'
    attendance_date = request.POST.get("attendance_date")
    attendance = Attendance.objects.get(id=attendance_date)

    attendance_data = AttendanceReport.objects.filter(attendance_id=attendance)
    # Only Passing Student Id and Student Name Only
    list_data = []

    for student in attendance_data:
        data_small = {
            "id": student.student_id.admin.id,
            "name": student.student_id.admin.first_name
            + " "
            + student.student_id.admin.last_name,
            "status": student.status,
        }
        list_data.append(data_small)

    return JsonResponse(
        json.dumps(list_data), content_type="application/json", safe=False
    )


@csrf_exempt
def update_attendance_data(request):
    student_ids = request.POST.get("student_ids")

    attendance_date = request.POST.get("attendance_date")
    attendance = Attendance.objects.get(id=attendance_date)

    json_student = json.loads(student_ids)

    try:
        for stud in json_student:
            # Attendance of Individual Student saved on AttendanceReport Model
            student = Students.objects.get(admin=stud["id"])

            attendance_report = AttendanceReport.objects.get(
                student_id=student, attendance_id=attendance
            )
            attendance_report.status = stud["status"]

            attendance_report.save()
        return HttpResponse("OK")
    except:
        return HttpResponse("Error")


def staff_profile(request):
    user = CustomUser.objects.get(id=request.user.id)
    staff = Staffs.objects.get(admin=user)

    context = {"user": user, "staff": staff}
    return render(request, "staff_template/staff_profile.html", context)


def staff_profile_update(request):
    if request.method != "POST":
        messages.error(request, "Invalid Method!")
        return redirect("staff_profile")
    else:
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        password = request.POST.get("password")
        address = request.POST.get("address")

        try:
            customuser = CustomUser.objects.get(id=request.user.id)
            customuser.first_name = first_name
            customuser.last_name = last_name
            if password != None and password != "":
                customuser.set_password(password)
            customuser.save()

            staff = Staffs.objects.get(admin=customuser.id)
            staff.address = address
            staff.save()

            messages.success(request, "Profile Updated Successfully")
            return redirect("staff_profile")
        except:
            messages.error(request, "Failed to Update Profile")
            return redirect("staff_profile")


def staff_add_result(request):
    subjects = Subjects.objects.filter(staff_id=request.user.id)
    session_years = SessionYearModel.objects.all()
    context = {
        "subjects": subjects,
        "session_years": session_years,
    }
    return render(request, "staff_template/add_result_template.html", context)


def staff_add_result_save(request):
    if request.method != "POST":
        messages.error(request, "Invalid Method")
        return redirect("staff_add_result")
    else:
        student_admin_id = request.POST.get("student_list")
        assignment_marks = request.POST.get("assignment_marks")
        exam_marks = request.POST.get("exam_marks")
        subject_id = request.POST.get("subject")

        student_obj = Students.objects.get(admin=student_admin_id)
        subject_obj = Subjects.objects.get(id=subject_id)

        try:
            # Check if Students Result Already Exists or not
            check_exist = StudentResult.objects.filter(
                subject_id=subject_obj, student_id=student_obj
            ).exists()
            if check_exist:
                result = StudentResult.objects.get(
                    subject_id=subject_obj, student_id=student_obj
                )
                result.subject_assignment_marks = assignment_marks
                result.subject_exam_marks = exam_marks
                result.save()
                messages.success(request, "Result Updated Successfully!")
                return redirect("staff_add_result")
            else:
                result = StudentResult(
                    student_id=student_obj,
                    subject_id=subject_obj,
                    subject_exam_marks=exam_marks,
                    subject_assignment_marks=assignment_marks,
                )
                result.save()
                messages.success(request, "Result Added Successfully!")
                return redirect("staff_add_result")
        except:
            messages.error(request, "Failed to Add Result!")
            return redirect("staff_add_result")


@login_required
def manage_assignments(request):
    staff = Staffs.objects.get(admin=request.user)
    subjects = Subjects.objects.filter(staff_id=request.user)
    assignments = Assignment.objects.filter(subject_id__in=subjects)
    context = {"assignments": assignments, "page_title": "Manage Assignments"}
    return render(request, "staff_template/manage_assignments.html", context)


@login_required
def add_assignment(request):
    subjects = Subjects.objects.filter(staff_id=request.user)
    context = {"subjects": subjects, "page_title": "Add Assignment"}
    return render(request, "staff_template/add_assignment.html", context)


@login_required
def add_assignment_save(request):
    if request.method != "POST":
        messages.error(request, "Invalid Method")
        return redirect("staff_manage_assignments")
    else:
        subject_id = request.POST.get("subject")
        title = request.POST.get("title")
        description = request.POST.get("description")
        due_date = request.POST.get("due_date")

        try:
            subject = Subjects.objects.get(id=subject_id)
            assignment = Assignment(
                subject_id=subject,
                title=title,
                description=description,
                due_date=due_date,
            )
            assignment.save()
            messages.success(request, "Assignment Added Successfully!")
            return redirect("staff_manage_assignments")
        except Exception as e:
            messages.error(request, f"Could Not Add Assignment: {str(e)}")
            return redirect("staff_add_assignment")


@login_required
def view_assignment_submissions(request, assignment_id):
    try:
        assignment = Assignment.objects.get(id=assignment_id)
        submissions = AssignmentSubmission.objects.filter(assignment_id=assignment)
        context = {
            "assignment": assignment,
            "submissions": submissions,
            "page_title": f"Submissions for {assignment.title}",
        }
        return render(
            request, "staff_template/view_assignment_submissions.html", context
        )
    except Assignment.DoesNotExist:
        messages.error(request, "Assignment Not Found")
        return redirect("staff_manage_assignments")


@login_required
@csrf_protect
def grade_assignment(request, submission_id):
    if request.method != "POST":
        return HttpResponse("Method Not Allowed")

    try:
        marks = request.POST.get("marks")

        if not marks:
            return HttpResponse("Missing required fields")

        try:
            marks = float(marks)
            if marks < 0:
                return HttpResponse("Marks cannot be negative")
        except ValueError:
            return HttpResponse("Invalid marks value")

        submission = AssignmentSubmission.objects.get(id=submission_id)

        if submission.assignment_id.subject_id.staff_id != request.user:
            return HttpResponse("You don't have permission to grade this submission")

        submission.marks = marks
        submission.status = "graded"
        submission.save()
        return HttpResponse("OK")
    except AssignmentSubmission.DoesNotExist:
        return HttpResponse("Submission not found")
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}")


@login_required
def delete_assignment(request, assignment_id):
    try:
        assignment = Assignment.objects.get(id=assignment_id)
        # Check if the staff member is authorized to delete this assignment
        if assignment.subject_id.staff_id != request.user:
            messages.error(request, "You are not authorized to delete this assignment")
            return redirect("staff_manage_assignments")

        # Delete the assignment
        assignment.delete()
        messages.success(request, "Assignment deleted successfully")
    except Assignment.DoesNotExist:
        messages.error(request, "Assignment not found")

    return redirect("staff_manage_assignments")


def manage_fines(request):
    fines = Fine.objects.all()
    context = {"fines": fines}
    return render(request, "staff_template/manage_fines_template.html", context)


def add_fine(request):
    students = Students.objects.all()
    context = {"students": students}
    return render(request, "staff_template/add_fine_template.html", context)


def add_fine_save(request):
    if request.method != "POST":
        messages.error(request, "Invalid Method")
        return redirect("manage_fines")
    else:
        student_id = request.POST.get("student")
        amount = request.POST.get("amount")
        reason = request.POST.get("reason")
        due_date = request.POST.get("due_date")

        try:
            student = Students.objects.get(id=student_id)
            fine = Fine(
                student_id=student,
                amount=float(amount),
                reason=reason,
                due_date=due_date,
            )
            fine.save()

            # Send email notification to student
            subject = "New Fine Added"
            message = f"""Dear {student.admin.first_name} {student.admin.last_name},

A new fine has been added to your account:

Amount: ₹{amount}
Reason: {reason}
Due Date: {due_date}

Please log in to your student portal to pay the fine.

Best regards,
Student Management System"""

            from_email = settings.EMAIL_HOST_USER
            recipient_list = [student.admin.email]
            try:
                send_mail(subject, message, from_email, recipient_list)
            except Exception as e:
                print(f"Failed to send fine notification email: {str(e)}")

            messages.success(request, "Fine added successfully")
            return redirect("manage_fines")
        except Exception as e:
            messages.error(request, f"Failed to add fine: {str(e)}")
            return redirect("add_fine")


def delete_fine(request, fine_id):
    try:
        fine = Fine.objects.get(id=fine_id, paid=False)
        fine.delete()
        messages.success(request, "Fine deleted successfully")
    except Fine.DoesNotExist:
        messages.error(request, "Fine not found or already paid")
    except Exception as e:
        messages.error(request, f"Error deleting fine: {str(e)}")
    return redirect("manage_fines")
