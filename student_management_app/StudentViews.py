import datetime
import json

import razorpay
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import serializers
from django.core.files.storage import FileSystemStorage
from django.core.mail import send_mail
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from student_management_app.models import (Assignment, AssignmentSubmission,
                                           Attendance, AttendanceReport,
                                           Courses, CustomUser,
                                           FeedBackStudent, Fine,
                                           LeaveReportStudent, StudentResult,
                                           Students, Subjects)


def student_home(request):
    student_obj = Students.objects.get(admin=request.user.id)
    total_attendance = AttendanceReport.objects.filter(student_id=student_obj).count()
    attendance_present = AttendanceReport.objects.filter(
        student_id=student_obj, status=True
    ).count()
    attendance_absent = AttendanceReport.objects.filter(
        student_id=student_obj, status=False
    ).count()

    course_obj = Courses.objects.get(id=student_obj.course_id.id)
    total_subjects = Subjects.objects.filter(course_id=course_obj).count()

    subject_name = []
    data_present = []
    data_absent = []
    subject_data = Subjects.objects.filter(course_id=student_obj.course_id)
    for subject in subject_data:
        attendance = Attendance.objects.filter(subject_id=subject.id)
        attendance_present_count = AttendanceReport.objects.filter(
            attendance_id__in=attendance, status=True, student_id=student_obj.id
        ).count()
        attendance_absent_count = AttendanceReport.objects.filter(
            attendance_id__in=attendance, status=False, student_id=student_obj.id
        ).count()
        subject_name.append(subject.subject_name)
        data_present.append(attendance_present_count)
        data_absent.append(attendance_absent_count)

    context = {
        "total_attendance": total_attendance,
        "attendance_present": attendance_present,
        "attendance_absent": attendance_absent,
        "total_subjects": total_subjects,
        "subject_name": subject_name,
        "data_present": data_present,
        "data_absent": data_absent,
    }
    return render(request, "student_template/student_home_template.html", context)


def student_view_attendance(request):
    student = Students.objects.get(
        admin=request.user.id
    )  # Getting Logged in Student Data
    course = student.course_id  # Getting Course Enrolled of LoggedIn Student
    # course = Courses.objects.get(id=student.course_id.id) # Getting Course Enrolled of LoggedIn Student
    subjects = Subjects.objects.filter(
        course_id=course
    )  # Getting the Subjects of Course Enrolled
    context = {"subjects": subjects}
    return render(request, "student_template/student_view_attendance.html", context)


def student_view_attendance_post(request):
    if request.method != "POST":
        messages.error(request, "Invalid Method")
        return redirect("student_view_attendance")
    else:
        # Getting all the Input Data
        subject_id = request.POST.get("subject")
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")

        # Parsing the date data into Python object
        start_date_parse = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date_parse = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()

        # Getting all the Subject Data based on Selected Subject
        subject_obj = Subjects.objects.get(id=subject_id)
        # Getting Logged In User Data
        user_obj = CustomUser.objects.get(id=request.user.id)
        # Getting Student Data Based on Logged in Data
        stud_obj = Students.objects.get(admin=user_obj)

        # Now Accessing Attendance Data based on the Range of Date Selected and Subject Selected
        attendance = Attendance.objects.filter(
            attendance_date__range=(start_date_parse, end_date_parse),
            subject_id=subject_obj,
        )
        # Getting Attendance Report based on the attendance details obtained above
        attendance_reports = AttendanceReport.objects.filter(
            attendance_id__in=attendance, student_id=stud_obj
        )

        # for attendance_report in attendance_reports:
        #     print("Date: "+ str(attendance_report.attendance_id.attendance_date), "Status: "+ str(attendance_report.status))

        # messages.success(request, "Attendacne View Success")

        context = {"subject_obj": subject_obj, "attendance_reports": attendance_reports}

        return render(request, "student_template/student_attendance_data.html", context)


def student_apply_leave(request):
    student_obj = Students.objects.get(admin=request.user.id)
    leave_data = LeaveReportStudent.objects.filter(student_id=student_obj)
    context = {"leave_data": leave_data}
    return render(request, "student_template/student_apply_leave.html", context)


def student_apply_leave_save(request):
    if request.method != "POST":
        messages.error(request, "Invalid Method")
        return redirect("student_apply_leave")
    else:
        leave_date = request.POST.get("leave_date")
        leave_message = request.POST.get("leave_message")

        student_obj = Students.objects.get(admin=request.user.id)
        try:
            leave_report = LeaveReportStudent(
                student_id=student_obj,
                leave_date=leave_date,
                leave_message=leave_message,
                leave_status=0,
            )
            leave_report.save()
            messages.success(request, "Applied for Leave.")
            return redirect("student_apply_leave")
        except:
            messages.error(request, "Failed to Apply Leave")
            return redirect("student_apply_leave")


def student_feedback(request):
    student_obj = Students.objects.get(admin=request.user.id)
    feedback_data = FeedBackStudent.objects.filter(student_id=student_obj)
    context = {"feedback_data": feedback_data}
    return render(request, "student_template/student_feedback.html", context)


def student_feedback_save(request):
    if request.method != "POST":
        messages.error(request, "Invalid Method.")
        return redirect("student_feedback")
    else:
        feedback = request.POST.get("feedback_message")
        student_obj = Students.objects.get(admin=request.user.id)

        try:
            add_feedback = FeedBackStudent(
                student_id=student_obj, feedback=feedback, feedback_reply=""
            )
            add_feedback.save()
            messages.success(request, "Feedback Sent.")
            return redirect("student_feedback")
        except:
            messages.error(request, "Failed to Send Feedback.")
            return redirect("student_feedback")


def student_profile(request):
    user = CustomUser.objects.get(id=request.user.id)
    student = Students.objects.get(admin=user)

    context = {"user": user, "student": student}
    return render(request, "student_template/student_profile.html", context)


def student_profile_update(request):
    if request.method != "POST":
        messages.error(request, "Invalid Method!")
        return redirect("student_profile")
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

            student = Students.objects.get(admin=customuser.id)
            student.address = address
            student.save()

            messages.success(request, "Profile Updated Successfully")
            return redirect("student_profile")
        except:
            messages.error(request, "Failed to Update Profile")
            return redirect("student_profile")


def student_view_result(request):
    student = Students.objects.get(admin=request.user.id)
    student_result = StudentResult.objects.filter(student_id=student.id)
    context = {
        "student_result": student_result,
    }
    return render(request, "student_template/student_view_result.html", context)


@login_required
def view_assignments(request):
    student = Students.objects.get(admin=request.user)
    # Fix: Filter assignments based on student's course subjects
    subjects = Subjects.objects.filter(course_id=student.course_id)
    assignments = Assignment.objects.filter(subject_id__in=subjects)

    # Get student's submissions
    submissions = AssignmentSubmission.objects.filter(student_id=student)
    submissions_dict = {sub.assignment_id.id: sub for sub in submissions}

    context = {
        "assignments": assignments,
        "submissions": submissions_dict,
        "now": timezone.now(),
        "page_title": "View Assignments",
    }
    return render(request, "student_template/view_assignments.html", context)


@login_required
def submit_assignment(request, assignment_id):
    if request.method != "POST":
        messages.error(request, "Invalid Method")
        return redirect("student_view_assignments")

    try:
        assignment = Assignment.objects.get(id=assignment_id)
        student = Students.objects.get(admin=request.user)

        # Check if assignment is past due date
        if timezone.now() > assignment.due_date:
            messages.error(request, "Assignment submission deadline has passed")
            return redirect("student_view_assignments")

        # Check if student has already submitted
        if AssignmentSubmission.objects.filter(
            student_id=student, assignment_id=assignment
        ).exists():
            messages.error(request, "You have already submitted this assignment")
            return redirect("student_view_assignments")

        if "submission_file" not in request.FILES:
            messages.error(request, "Please select a file to submit")
            return redirect("student_view_assignments")

        submission_file = request.FILES["submission_file"]
        fs = FileSystemStorage()
        filename = fs.save(
            f"assignments/submissions/{student.id}_{assignment_id}_{submission_file.name}",
            submission_file,
        )

        submission = AssignmentSubmission(
            student_id=student, assignment_id=assignment, submission_file=filename
        )
        submission.save()
        messages.success(request, "Assignment submitted successfully")
        return redirect("student_view_assignments")
    except Exception as e:
        messages.error(request, f"Error submitting assignment: {str(e)}")
        return redirect("student_view_assignments")


def student_view_fines(request):
    student = Students.objects.get(admin=request.user)
    fines = Fine.objects.filter(student_id=student, paid=False)
    context = {"fines": fines}
    return render(request, "student_template/student_view_fines.html", context)


def initialize_payment(request, fine_id):
    try:
        fine = Fine.objects.get(id=fine_id, student_id__admin=request.user, paid=False)
        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

        # Convert amount to paise (Razorpay expects amount in smallest currency unit)
        amount_in_paise = int(fine.amount * 100)

        payment_data = {
            "amount": amount_in_paise,
            "currency": "INR",
            "receipt": f"fine_{fine.id}",
            "notes": {
                "fine_id": fine.id,
                "student_id": fine.student_id.id,
                "reason": fine.reason,
            },
        }

        order = client.order.create(data=payment_data)

        context = {
            "fine": fine,
            "razorpay_key": settings.RAZORPAY_KEY_ID,
            "amount_in_paise": amount_in_paise,
            "currency": "INR",
            "order_id": order["id"],
        }

        return render(request, "student_template/payment_page.html", context)
    except Fine.DoesNotExist:
        messages.error(request, "Fine not found or already paid")
        return redirect("student_view_fines")
    except Exception as e:
        messages.error(request, f"Error initializing payment: {str(e)}")
        return redirect("student_view_fines")


@csrf_exempt
def payment_callback(request):
    try:
        # Get payment details from request
        payment_id = request.GET.get("razorpay_payment_id")
        order_id = request.GET.get("razorpay_order_id")
        signature = request.GET.get("razorpay_signature")

        # Initialize Razorpay client
        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

        # Verify payment signature
        params_dict = {
            "razorpay_payment_id": payment_id,
            "razorpay_order_id": order_id,
            "razorpay_signature": signature,
        }

        try:
            client.utility.verify_payment_signature(params_dict)

            # Get order details
            order = client.order.fetch(order_id)

            # Extract fine_id from receipt
            fine_id = int(order["receipt"].split("_")[1])

            # Update fine status
            fine = Fine.objects.get(id=fine_id)
            fine.paid = True
            fine.payment_id = payment_id
            fine.payment_date = timezone.now()
            fine.save()

            # Try to send confirmation email
            try:
                subject = "Fine Payment Confirmation"
                message = f"""Dear {fine.student_id.admin.first_name},
                
Your fine payment of ₹{fine.amount} for {fine.reason} has been received.
Payment ID: {payment_id}
Date: {fine.payment_date}

Thank you for your payment.

Best regards,
Student Management System"""

                send_mail(
                    subject,
                    message,
                    settings.EMAIL_HOST_USER,
                    [fine.student_id.admin.email],
                    fail_silently=True,
                )
            except Exception as email_error:
                # Log the email error but don't fail the payment process
                print(f"Failed to send confirmation email: {str(email_error)}")

            messages.success(
                request, "Payment successful! A confirmation email has been sent."
            )
            return redirect("student_view_fines")

        except Exception as e:
            messages.error(request, f"Payment verification failed: {str(e)}")
            return redirect("student_view_fines")

    except Exception as e:
        messages.error(request, f"Error processing payment: {str(e)}")
        return redirect("student_view_fines")
