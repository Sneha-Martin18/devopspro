import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods

from .utils import (APIClient, get_user_data, get_user_type, is_authenticated,
                    require_auth, require_user_type)

logger = logging.getLogger(__name__)


# Authentication Views
def csrf_failure(request, reason=""):
    """Custom CSRF failure view"""
    logger.warning(f"CSRF verification failed: {reason}")
    messages.error(request, "Session expired. Please refresh the page and try again.")
    return redirect("login")


def login_page(request):
    """Login page view"""
    # Clear any existing session data to prevent redirect loops
    if "next" in request.GET and not request.session.get("is_authenticated"):
        return render(request, "login.html", {"next": request.GET["next"]})

    if request.session.get("is_authenticated"):
        user_type = str(request.session.get("user_type", "0"))
        if user_type == "1":  # HOD
            return redirect("admin_home")
        elif user_type == "2":  # Staff
            return redirect("staff_home")
        elif user_type == "3":  # Student
            return redirect("student_home")

    return render(request, "login.html")


from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.debug import sensitive_post_parameters


@sensitive_post_parameters()
@csrf_protect
def doLogin(request):
    """Handle login authentication with CSRF protection"""
    logger.info(f"Login attempt - Method: {request.method}")

    if request.method == "GET":
        # Create a response with the login form
        response = render(request, "login.html", {"next": request.GET.get("next", "")})

        # Ensure CSRF token is set in the cookie
        if not request.META.get("CSRF_COOKIE"):
            csrf_token = get_token(request)
            response.set_cookie(
                settings.CSRF_COOKIE_NAME,
                csrf_token,
                max_age=settings.CSRF_COOKIE_AGE,
                domain=settings.SESSION_COOKIE_DOMAIN,
                path=settings.CSRF_COOKIE_PATH,
                secure=settings.CSRF_COOKIE_SECURE,
                httponly=settings.CSRF_COOKIE_HTTPONLY,
                samesite=settings.CSRF_COOKIE_SAMESITE,
            )
            logger.debug("CSRF cookie set in login page response")

        return response

    # Handle POST request
    try:
        # Get form data
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "").strip()
        next_url = request.POST.get("next", "").strip()

        logger.info(f"Login attempt - Email: {email}")

        if not email or not password:
            logger.warning("Login failed - Missing email or password")
            messages.error(request, "Email and password are required")
            return render(request, "login.html", {"next": next_url})

        # Authenticate with API Gateway
        try:
            import requests
            
            # Call the login API
            api_url = f"{settings.API_GATEWAY_URL}/api/v1/users/login/"
            login_data = {
                "username": email,  # User service expects username field
                "password": password
            }
            
            logger.info(f"Attempting API login for: {email}")
            response = requests.post(api_url, json=login_data, timeout=10)
            
            if response.status_code == 200:
                auth_data = response.json()
                logger.info(f"API login successful: {auth_data}")
                
                # Clear existing session
                request.session.flush()
                
                # Extract user data and token
                user_data = auth_data.get("user", {})
                access_token = auth_data.get("access_token")
                
                if not access_token:
                    logger.error("No access token in response")
                    messages.error(request, "Authentication failed - no token received")
                    return render(request, "login.html", {"next": next_url})
                
                # Set session data
                request.session["user_id"] = str(user_data.get("id", ""))
                request.session["user_type"] = str(user_data.get("user_type", "0"))
                request.session["user_email"] = user_data.get("email", email)
                request.session["user_data"] = user_data
                request.session["is_authenticated"] = True
                request.session["api_token"] = access_token
                request.session["refresh_token"] = auth_data.get("refresh_token", "")
                request.session["_auth_user_id"] = str(user_data.get("id", ""))
                request.session["_auth_user_backend"] = "django.contrib.auth.backends.ModelBackend"
                
                # Save session
                request.session.save()
                logger.info(f"Session data set - user_id: {user_data.get('id')}, user_type: {user_data.get('user_type')}")
                
                # Determine redirect URL based on user type
                user_type = str(user_data.get("user_type", "0"))
                if not next_url:
                    if user_type == "1":  # HOD
                        next_url = "admin_home"
                    elif user_type == "2":  # Staff
                        next_url = "staff_home"
                    elif user_type == "3":  # Student
                        next_url = "student_home"
                    else:
                        next_url = "login"
                
                # Create response with redirect
                response = redirect(next_url)
                
                # Ensure CSRF cookie is set
                if not request.COOKIES.get(settings.CSRF_COOKIE_NAME):
                    csrf_token = get_token(request)
                    response.set_cookie(
                        settings.CSRF_COOKIE_NAME,
                        csrf_token,
                        max_age=settings.CSRF_COOKIE_AGE,
                        domain=settings.SESSION_COOKIE_DOMAIN,
                        path=settings.CSRF_COOKIE_PATH,
                        secure=settings.CSRF_COOKIE_SECURE,
                        httponly=settings.CSRF_COOKIE_HTTPONLY,
                        samesite=settings.CSRF_COOKIE_SAMESITE,
                    )
                    logger.debug("CSRF cookie set in response")
                
                messages.success(request, "Login successful!")
                logger.info(f"Redirecting to: {next_url}")
                return response
            else:
                logger.warning(f"API login failed - Status: {response.status_code}, Response: {response.text}")
                messages.error(request, "Invalid email or password")
                return render(request, "login.html", {"next": next_url})
                
        except requests.RequestException as e:
            logger.error(f"API login request failed: {str(e)}")
            messages.error(request, "Authentication service unavailable. Please try again later.")
            return render(request, "login.html", {"next": next_url})
        except Exception as e:
            logger.error(f"Unexpected error during login: {str(e)}")
            messages.error(request, "An error occurred during login. Please try again.")
            return render(request, "login.html", {"next": next_url})

    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        messages.error(request, "An error occurred during login. Please try again.")
        return render(request, "login.html", {"next": request.POST.get("next", "")})

    # If not POST, show login page
    logger.warning("Non-POST request to login")
    return render(request, "login.html")


def logout_user(request):
    """Logout user and clear session"""
    logout(request)
    request.session.flush()
    messages.success(request, "Successfully logged out")
    return redirect("login")


# HOD Views
@require_user_type(["1"])
def admin_home(request):
    """HOD dashboard with statistics from all services"""
    api_client = APIClient(request)

    # Get statistics from various services
    context = {
        "user_data": get_user_data(request),
        "all_student_count": 0,
        "staff_count": 0,
        "course_count": 0,
        "subject_count": 0,
        "course_name_list": [],
        "subject_count_list": [],
        "student_count_list_in_course": [],
        "student_count_list_in_subject": [],
        "subject_list": [],
        "staff_attendance_present_list": [],
        "staff_attendance_leave_list": [],
        "staff_name_list": [],
        "student_attendance_present_list": [],
        "student_attendance_leave_list": [],
        "student_name_list": [],
    }

    # Get user statistics
    users_data = api_client.get("/api/v1/users/")
    if users_data:
        context["all_student_count"] = len(
            [u for u in users_data.get("results", []) if u.get("user_type") == 3]
        )
        context["staff_count"] = len(
            [u for u in users_data.get("results", []) if u.get("user_type") == 2]
        )

    # Get academic statistics
    courses_data = api_client.get("/api/v1/academics/courses/")
    if courses_data:
        context["course_count"] = courses_data.get("count", 0)
        courses = courses_data.get("results", [])
        context["course_name_list"] = [
            course.get("course_name", "") for course in courses
        ]

    subjects_data = api_client.get("/api/v1/academics/subjects/")
    if subjects_data:
        context["subject_count"] = subjects_data.get("count", 0)
        subjects = subjects_data.get("results", [])
        context["subject_list"] = [
            subject.get("subject_name", "") for subject in subjects
        ]

    # Mock data for charts (replace with actual API calls)
    context["subject_count_list"] = (
        [5, 3, 4, 2] if len(context["course_name_list"]) > 0 else []
    )
    context["student_count_list_in_course"] = (
        [25, 30, 20, 15] if len(context["course_name_list"]) > 0 else []
    )
    context["student_count_list_in_subject"] = (
        [10, 15, 8, 12] if len(context["subject_list"]) > 0 else []
    )
    context["staff_name_list"] = ["John Doe", "Jane Smith", "Bob Wilson"]
    context["staff_attendance_present_list"] = [20, 18, 22]
    context["staff_attendance_leave_list"] = [2, 4, 1]
    context["student_name_list"] = ["Alice Brown", "Charlie Davis", "Eva Green"]
    context["student_attendance_present_list"] = [25, 28, 30]
    context["student_attendance_leave_list"] = [3, 2, 1]

    return render(request, "hod_template/home_content.html", context)


@require_user_type(["1"])
def admin_profile(request):
    """HOD profile view"""
    user_data = get_user_data(request)
    return render(request, "hod_template/admin_profile.html", {"user_data": user_data})


@require_user_type(["1"])
def admin_profile_update(request):
    """Update HOD profile via API"""
    if request.method == "POST":
        api_client = APIClient(request)
        user_data = get_user_data(request)

        update_data = {
            "first_name": request.POST.get("first_name"),
            "last_name": request.POST.get("last_name"),
            "email": request.POST.get("email"),
        }

        result = api_client.put(f'/api/v1/users/{user_data.get("id")}/', update_data)
        if result:
            messages.success(request, "Profile updated successfully")
            # Update session data
            request.session["user_data"].update(update_data)
        else:
            messages.error(request, "Failed to update profile")

    return redirect("admin_profile")


# Course Management Views
@require_user_type(["1"])
def add_course(request):
    """Add course form"""
    return render(request, "hod_template/add_course_template.html")


@require_user_type(["1"])
def add_course_save(request):
    """Save new course via API"""
    if request.method == "POST":
        api_client = APIClient(request)

        course_data = {
            "course_name": request.POST.get("course_name"),
            "course_code": request.POST.get("course_code"),
            "description": request.POST.get("description", ""),
        }

        result = api_client.post("/api/v1/academics/courses/", course_data)
        if result:
            messages.success(request, "Course added successfully")
        else:
            messages.error(request, "Failed to add course")

    return redirect("manage_course")


@require_user_type(["1"])
def manage_course(request):
    """Manage courses view"""
    api_client = APIClient(request)
    courses_data = api_client.get("/api/v1/academics/courses/")

    context = {"courses": courses_data.get("results", []) if courses_data else []}
    return render(request, "hod_template/manage_course_template.html", context)


@require_user_type(["1"])
def edit_course(request, course_id):
    """Edit course form"""
    api_client = APIClient(request)
    course_data = api_client.get(f"/api/v1/academics/courses/{course_id}/")

    context = {"course": course_data if course_data else {}}
    return render(request, "hod_template/edit_course_template.html", context)


@require_user_type(["1"])
def edit_course_save(request):
    """Save course updates via API"""
    if request.method == "POST":
        api_client = APIClient(request)
        course_id = request.POST.get("course_id")

        course_data = {
            "course_name": request.POST.get("course_name"),
            "course_code": request.POST.get("course_code"),
            "description": request.POST.get("description", ""),
        }

        result = api_client.put(f"/api/v1/academics/courses/{course_id}/", course_data)
        if result:
            messages.success(request, "Course updated successfully")
        else:
            messages.error(request, "Failed to update course")

    return redirect("manage_course")


@require_user_type(["1"])
def delete_course(request, course_id):
    """Delete course via API"""
    api_client = APIClient(request)
    result = api_client.delete(f"/api/v1/academics/courses/{course_id}/")

    if result:
        messages.success(request, "Course deleted successfully")
    else:
        messages.error(request, "Failed to delete course")

    return redirect("manage_course")


# Subject Management Views
@require_user_type(["1"])
def add_subject(request):
    """Add subject form"""
    api_client = APIClient(request)
    courses_data = api_client.get("/api/v1/academics/courses/")
    staff_data = api_client.get("/api/v1/users/?user_type=2")

    context = {
        "courses": courses_data.get("results", []) if courses_data else [],
        "staff_list": staff_data.get("results", []) if staff_data else [],
    }
    return render(request, "hod_template/add_subject_template.html", context)


@require_user_type(["1"])
def add_subject_save(request):
    """Save new subject via API"""
    if request.method == "POST":
        api_client = APIClient(request)

        subject_data = {
            "subject_name": request.POST.get("subject_name"),
            "subject_code": request.POST.get("subject_code"),
            "course_id": request.POST.get("course_id"),
            "staff_id": request.POST.get("staff_id"),
            "description": request.POST.get("description", ""),
        }

        result = api_client.post("/api/v1/academics/subjects/", subject_data)
        if result:
            messages.success(request, "Subject added successfully")
        else:
            messages.error(request, "Failed to add subject")

    return redirect("manage_subject")


@require_user_type(["1"])
def manage_subject(request):
    """Manage subjects view"""
    api_client = APIClient(request)
    subjects_data = api_client.get("/api/v1/academics/subjects/")

    context = {"subjects": subjects_data.get("results", []) if subjects_data else []}
    return render(request, "hod_template/manage_subject_template.html", context)


# Staff Management Views
@require_user_type(["1"])
def add_staff(request):
    """Add staff form"""
    return render(request, "hod_template/add_staff_template.html")


@require_user_type(["1"])
def add_staff_save(request):
    """Save new staff via API"""
    if request.method == "POST":
        api_client = APIClient(request)

        staff_data = {
            "email": request.POST.get("email"),
            "password": request.POST.get("password"),
            "first_name": request.POST.get("first_name"),
            "last_name": request.POST.get("last_name"),
            "address": request.POST.get("address", ""),
        }

        result = api_client.post("/api/v1/users/staff/", staff_data)
        if result:
            messages.success(request, "Staff added successfully")
        else:
            messages.error(request, "Failed to add staff")

    return redirect("manage_staff")


@require_user_type(["1"])
def manage_staff(request):
    """Manage staff view"""
    api_client = APIClient(request)
    staff_data = api_client.get("/api/v1/users/staff/")

    context = {"staff_list": staff_data.get("results", []) if staff_data else []}
    return render(request, "hod_template/manage_staff_template.html", context)


# Student Management Views
@require_user_type(["1"])
def add_student(request):
    """Add student form"""
    from .forms import AddStudentForm
    
    api_client = APIClient(request)
    courses_data = api_client.get("/api/v1/academics/courses/")
    sessions_data = api_client.get("/api/v1/academics/session-years/")

    courses = courses_data.get("results", []) if courses_data else []
    sessions = sessions_data.get("results", []) if sessions_data else []
    
    form = AddStudentForm(courses=courses, sessions=sessions)
    
    context = {
        "form": form,
    }
    return render(request, "hod_template/add_student_template.html", context)


@require_user_type(["1"])
def add_student_save(request):
    """Save new student via API"""
    if request.method == "POST":
        api_client = APIClient(request)

        student_data = {
            "email": request.POST.get("email"),
            "password": request.POST.get("password"),
            "first_name": request.POST.get("first_name"),
            "last_name": request.POST.get("last_name"),
            "user_type": "3",  # Student
            "address": request.POST.get("address", ""),
            "course_id": request.POST.get("course_id"),
            "session_year_id": request.POST.get("session_year_id"),
        }

        result = api_client.post("/api/v1/users/", student_data)
        if result:
            messages.success(request, "Student added successfully")
        else:
            messages.error(request, "Failed to add student")

    return redirect("manage_student")


@require_user_type(["1"])
def manage_student(request):
    """Manage students view"""
    api_client = APIClient(request)
    students_data = api_client.get("/api/v1/users/?user_type=3")

    context = {"students": students_data.get("results", []) if students_data else []}
    return render(request, "hod_template/manage_student_template.html", context)


# Session Management Views
@require_user_type(["1"])
def add_session(request):
    """Add session form"""
    return render(request, "hod_template/add_session_template.html")


@require_user_type(["1"])
def add_session_save(request):
    """Save new session via API"""
    if request.method == "POST":
        api_client = APIClient(request)

        session_data = {
            "session_start_year": request.POST.get("session_start_year"),
            "session_end_year": request.POST.get("session_end_year"),
        }

        result = api_client.post("/api/v1/academics/session-years/", session_data)
        if result:
            messages.success(request, "Session added successfully")
        else:
            messages.error(request, "Failed to add session")

    return redirect("manage_session")


@require_user_type(["1"])
def manage_session(request):
    """Manage sessions view"""
    api_client = APIClient(request)
    sessions_data = api_client.get("/api/v1/academics/session-years/")

    context = {"sessions": sessions_data.get("results", []) if sessions_data else []}
    return render(request, "hod_template/manage_session_template.html", context)


# Staff Views
@require_user_type(["2"])
def staff_home(request):
    """Staff dashboard"""
    api_client = APIClient(request)
    user_data = get_user_data(request)

    # Get staff-specific statistics
    context = {
        "user_data": user_data,
        "my_subjects": [],
        "today_attendance": 0,
        "pending_assignments": 0,
        "recent_submissions": [],
    }

    # Get subjects assigned to this staff
    subjects_data = api_client.get(
        f'/api/v1/academics/subjects/?staff_id={user_data.get("id")}'
    )
    if subjects_data:
        context["my_subjects"] = subjects_data.get("results", [])

    # Get attendance statistics
    attendance_data = api_client.get("/api/v1/attendance/stats/")
    if attendance_data:
        context["today_attendance"] = attendance_data.get("today_count", 0)

    # Get assignments
    assignments_data = api_client.get(
        f'/api/v1/assessments/assignments/?created_by={user_data.get("id")}'
    )
    if assignments_data:
        context["pending_assignments"] = len(
            [
                a
                for a in assignments_data.get("results", [])
                if a.get("status") == "published"
            ]
        )

    return render(request, "staff_template/home_content.html", context)


@require_user_type(["2"])
def staff_profile(request):
    """Staff profile view"""
    user_data = get_user_data(request)
    return render(
        request, "staff_template/staff_profile.html", {"user_data": user_data}
    )


# Student Views
@require_user_type(["3"])
def student_home(request):
    """Student dashboard"""
    api_client = APIClient(request)
    user_data = get_user_data(request)

    # Get student-specific data
    context = {
        "user_data": user_data,
        "my_attendance": {},
        "pending_assignments": [],
        "recent_grades": [],
        "outstanding_fees": 0,
    }

    # Get attendance data
    attendance_data = api_client.get(
        f'/api/v1/attendance/stats/?student_id={user_data.get("id")}'
    )
    if attendance_data:
        context["my_attendance"] = attendance_data

    # Get assignments
    assignments_data = api_client.get(
        "/api/v1/assessments/assignments/?status=published"
    )
    if assignments_data:
        context["pending_assignments"] = assignments_data.get("results", [])

    # Get grades
    grades_data = api_client.get(
        f'/api/v1/assessments/grades/?student_id={user_data.get("id")}'
    )
    if grades_data:
        context["recent_grades"] = grades_data.get("results", [])[:5]

    # Get financial data
    fees_data = api_client.get(
        f'/api/v1/finances/fees/?student_id={user_data.get("id")}&status=pending'
    )
    if fees_data:
        context["outstanding_fees"] = sum(
            float(fee.get("amount_due", 0)) for fee in fees_data.get("results", [])
        )

    return render(request, "student_template/home_content.html", context)


@require_user_type(["3"])
def student_profile(request):
    """Student profile view"""
    user_data = get_user_data(request)
    return render(
        request, "student_template/student_profile.html", {"user_data": user_data}
    )


# Attendance Views
@require_user_type(["2"])
def staff_take_attendance(request):
    """Staff take attendance form"""
    api_client = APIClient(request)
    user_data = get_user_data(request)

    # Get subjects assigned to this staff
    subjects_data = api_client.get(
        f'/api/v1/academics/subjects/?staff_id={user_data.get("id")}'
    )

    context = {"subjects": subjects_data.get("results", []) if subjects_data else []}
    return render(request, "staff_template/take_attendance_template.html", context)


@csrf_exempt
def save_attendance_data(request):
    """Save attendance data via API"""
    if request.method == "POST":
        api_client = APIClient(request)

        try:
            data = json.loads(request.body)
            result = api_client.post("/api/v1/attendance/bulk-mark/", data)

            if result:
                return JsonResponse({"status": "success"})
            else:
                return JsonResponse(
                    {"status": "error", "message": "Failed to save attendance"}
                )
        except Exception as e:
            logger.error(f"Error saving attendance: {e}")
            return JsonResponse({"status": "error", "message": str(e)})

    return JsonResponse({"status": "error", "message": "Invalid request method"})


# Fine Management Views
@require_user_type(["2"])
def staff_add_fine(request):
    """Staff add fine form"""
    api_client = APIClient(request)
    students_data = api_client.get("/api/v1/users/?user_type=3")

    context = {"students": students_data.get("results", []) if students_data else []}
    return render(request, "staff_template/add_fine_template.html", context)


@require_user_type(["2"])
def staff_add_fine_save(request):
    """Save new fine via API"""
    if request.method == "POST":
        api_client = APIClient(request)

        fine_data = {
            "student_id": request.POST.get("student_id"),
            "fine_type": request.POST.get("fine_type"),
            "amount": request.POST.get("amount"),
            "reason": request.POST.get("reason"),
            "due_date": request.POST.get("due_date"),
        }

        result = api_client.post("/api/v1/finances/fines/", fine_data)
        if result:
            messages.success(request, "Fine added successfully")
        else:
            messages.error(request, "Failed to add fine")

    return redirect("staff_manage_fines")


@require_user_type(["2"])
def staff_manage_fines(request):
    """Manage fines view"""
    api_client = APIClient(request)
    fines_data = api_client.get("/api/v1/finances/fines/")

    context = {"fines": fines_data.get("results", []) if fines_data else []}
    return render(request, "staff_template/manage_fines_template.html", context)


# Student Fine Views
@require_user_type(["3"])
def student_view_fines(request):
    """Student view fines"""
    api_client = APIClient(request)
    user_data = get_user_data(request)

    fines_data = api_client.get(
        f'/api/v1/finances/fines/?student_id={user_data.get("id")}'
    )

    context = {"fines": fines_data.get("results", []) if fines_data else []}
    return render(request, "student_template/student_view_fines.html", context)


# Utility Views
def health_check(request):
    """Health check endpoint"""
    return JsonResponse({"status": "ok"})


def debug_session(request):
    """Debug view to check session data"""
    session_data = dict(request.session)
    return JsonResponse(
        {
            "session_data": session_data,
            "is_authenticated": request.session.get("is_authenticated", False),
            "user_type": request.session.get("user_type"),
            "user_id": request.session.get("user_id"),
            "user_email": request.session.get("user_email"),
            "cookies": dict(request.COOKIES),
            "meta": {
                k: str(v) for k, v in request.META.items() if k.startswith("HTTP_")
            },
        }
    )


# AJAX Helper Views
@csrf_exempt
def get_students(request):
    """Get students for a subject via AJAX"""
    if request.method == "POST":
        api_client = APIClient(request)
        subject_id = request.POST.get("subject_id")

        # Get students enrolled in this subject
        students_data = api_client.get(
            f"/api/v1/academics/subject-enrollments/?subject_id={subject_id}"
        )

        if students_data:
            return JsonResponse({"students": students_data.get("results", [])})
        else:
            return JsonResponse({"students": []})

    return JsonResponse({"students": []})


# Placeholder views for remaining functionality
def edit_subject(request, subject_id):
    return redirect("manage_subject")


def edit_subject_save(request):
    return redirect("manage_subject")


def delete_subject(request, subject_id):
    return redirect("manage_subject")


def edit_staff(request, staff_id):
    return redirect("manage_staff")


def edit_staff_save(request):
    return redirect("manage_staff")


def delete_staff(request, staff_id):
    return redirect("manage_staff")


def edit_student(request, student_id):
    return redirect("manage_student")


def edit_student_save(request):
    return redirect("manage_student")


def delete_student(request, student_id):
    return redirect("manage_student")


def edit_session(request, session_id):
    return redirect("manage_session")


def edit_session_save(request):
    return redirect("manage_session")


def delete_session(request, session_id):
    return redirect("manage_session")


def admin_view_attendance(request):
    return render(request, "hod_template/admin_view_attendance.html")


def admin_get_attendance_dates(request):
    return JsonResponse({})


def admin_get_attendance_student(request):
    return JsonResponse({})


def admin_view_leave(request):
    return render(request, "hod_template/staff_leave_view.html")


def admin_approve_leave(request):
    return JsonResponse({})


def admin_disapprove_leave(request):
    return JsonResponse({})


def student_feedback_message(request):
    return render(request, "hod_template/student_feedback_template.html")


def student_feedback_message_reply(request):
    return JsonResponse({})


def staff_feedback_message(request):
    return render(request, "hod_template/staff_feedback_template.html")


def staff_feedback_message_reply(request):
    return JsonResponse({})


def send_student_notification(request):
    return render(request, "hod_template/notification_template.html")


def send_staff_notification(request):
    return render(request, "hod_template/notification_template.html")


def staff_update_attendance(request):
    return redirect("staff_take_attendance")


def staff_profile_update(request):
    return redirect("staff_profile")


def staff_add_result(request):
    return render(request, "staff_template/add_result_template.html")


def staff_add_result_save(request):
    return redirect("staff_add_result")


def staff_view_attendance(request):
    return render(request, "staff_template/staff_view_attendance.html")


def staff_apply_leave(request):
    return render(request, "staff_template/staff_apply_leave.html")


def staff_apply_leave_save(request):
    return redirect("staff_apply_leave")


def staff_feedback(request):
    return render(request, "staff_template/staff_feedback.html")


def staff_feedback_save(request):
    return redirect("staff_feedback")


def staff_edit_fine(request, fine_id):
    return redirect("staff_manage_fines")


def staff_edit_fine_save(request):
    return redirect("staff_manage_fines")


def staff_delete_fine(request, fine_id):
    return redirect("staff_manage_fines")


def student_view_attendance(request):
    return render(request, "student_template/student_view_attendance.html")


def student_view_attendance_post(request):
    return JsonResponse({})


def student_apply_leave(request):
    return render(request, "student_template/student_apply_leave.html")


def student_apply_leave_save(request):
    return redirect("student_apply_leave")


def student_feedback(request):
    return render(request, "student_template/student_feedback.html")


def student_feedback_save(request):
    return redirect("student_feedback")


def student_profile_update(request):
    return redirect("student_profile")


def student_view_result(request):
    return render(request, "student_template/student_view_result.html")


def student_pay_fine(request, fine_id):
    return render(request, "student_template/student_pay_fine.html")


def student_pay_fine_save(request):
    return redirect("student_view_fines")


def get_attendance_dates(request):
    return JsonResponse({})


def get_attendance_student(request):
    return JsonResponse({})


def update_attendance_data(request):
    return JsonResponse({})
