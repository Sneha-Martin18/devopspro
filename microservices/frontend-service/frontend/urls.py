from django.urls import path

from . import views

urlpatterns = [
    # Authentication URLs
    path("", views.login_page, name="login"),
    path("doLogin/", views.doLogin, name="doLogin"),
    path("logout_user/", views.logout_user, name="logout_user"),
    # HOD URLs
    path("admin_home/", views.admin_home, name="admin_home"),
    path("admin_profile/", views.admin_profile, name="admin_profile"),
    path(
        "admin_profile_update/", views.admin_profile_update, name="admin_profile_update"
    ),
    # Course Management
    path("add_course/", views.add_course, name="add_course"),
    path("add_course_save/", views.add_course_save, name="add_course_save"),
    path("manage_course/", views.manage_course, name="manage_course"),
    path("edit_course/<course_id>/", views.edit_course, name="edit_course"),
    path("edit_course_save/", views.edit_course_save, name="edit_course_save"),
    path("delete_course/<course_id>/", views.delete_course, name="delete_course"),
    # Subject Management
    path("add_subject/", views.add_subject, name="add_subject"),
    path("add_subject_save/", views.add_subject_save, name="add_subject_save"),
    path("manage_subject/", views.manage_subject, name="manage_subject"),
    path("edit_subject/<subject_id>/", views.edit_subject, name="edit_subject"),
    path("edit_subject_save/", views.edit_subject_save, name="edit_subject_save"),
    path("delete_subject/<subject_id>/", views.delete_subject, name="delete_subject"),
    # Staff Management
    path("add_staff/", views.add_staff, name="add_staff"),
    path("add_staff_save/", views.add_staff_save, name="add_staff_save"),
    path("manage_staff/", views.manage_staff, name="manage_staff"),
    path("edit_staff/<staff_id>/", views.edit_staff, name="edit_staff"),
    path("edit_staff_save/", views.edit_staff_save, name="edit_staff_save"),
    path("delete_staff/<staff_id>/", views.delete_staff, name="delete_staff"),
    # Student Management
    path("add_student/", views.add_student, name="add_student"),
    path("add_student_save/", views.add_student_save, name="add_student_save"),
    path("manage_student/", views.manage_student, name="manage_student"),
    path("edit_student/<student_id>/", views.edit_student, name="edit_student"),
    path("edit_student_save/", views.edit_student_save, name="edit_student_save"),
    path("delete_student/<student_id>/", views.delete_student, name="delete_student"),
    # Session Management
    path("add_session/", views.add_session, name="add_session"),
    path("add_session_save/", views.add_session_save, name="add_session_save"),
    path("manage_session/", views.manage_session, name="manage_session"),
    path("edit_session/<session_id>/", views.edit_session, name="edit_session"),
    path("edit_session_save/", views.edit_session_save, name="edit_session_save"),
    path("delete_session/<session_id>/", views.delete_session, name="delete_session"),
    # Attendance Management
    path(
        "admin_view_attendance/",
        views.admin_view_attendance,
        name="admin_view_attendance",
    ),
    path(
        "admin_get_attendance_dates/",
        views.admin_get_attendance_dates,
        name="admin_get_attendance_dates",
    ),
    path(
        "admin_get_attendance_student/",
        views.admin_get_attendance_student,
        name="admin_get_attendance_student",
    ),
    # Leave Management
    path("admin_view_leave/", views.admin_view_leave, name="admin_view_leave"),
    path("admin_approve_leave/", views.admin_approve_leave, name="admin_approve_leave"),
    path(
        "admin_disapprove_leave/",
        views.admin_disapprove_leave,
        name="admin_disapprove_leave",
    ),
    # Feedback Management
    path(
        "student_feedback_message/",
        views.student_feedback_message,
        name="student_feedback_message",
    ),
    path(
        "student_feedback_message_reply/",
        views.student_feedback_message_reply,
        name="student_feedback_message_reply",
    ),
    path(
        "staff_feedback_message/",
        views.staff_feedback_message,
        name="staff_feedback_message",
    ),
    path(
        "staff_feedback_message_reply/",
        views.staff_feedback_message_reply,
        name="staff_feedback_message_reply",
    ),
    # Notification Management
    path(
        "send_student_notification/",
        views.send_student_notification,
        name="send_student_notification",
    ),
    path(
        "send_staff_notification/",
        views.send_staff_notification,
        name="send_staff_notification",
    ),
    # Staff URLs
    path("staff_home/", views.staff_home, name="staff_home"),
    path(
        "staff_take_attendance/",
        views.staff_take_attendance,
        name="staff_take_attendance",
    ),
    path(
        "staff_update_attendance/",
        views.staff_update_attendance,
        name="staff_update_attendance",
    ),
    path("staff_profile/", views.staff_profile, name="staff_profile"),
    path(
        "staff_profile_update/", views.staff_profile_update, name="staff_profile_update"
    ),
    path("staff_add_result/", views.staff_add_result, name="staff_add_result"),
    path(
        "staff_add_result_save/",
        views.staff_add_result_save,
        name="staff_add_result_save",
    ),
    path(
        "staff_view_attendance/",
        views.staff_view_attendance,
        name="staff_view_attendance",
    ),
    path("staff_apply_leave/", views.staff_apply_leave, name="staff_apply_leave"),
    path(
        "staff_apply_leave_save/",
        views.staff_apply_leave_save,
        name="staff_apply_leave_save",
    ),
    path("staff_feedback/", views.staff_feedback, name="staff_feedback"),
    path("staff_feedback_save/", views.staff_feedback_save, name="staff_feedback_save"),
    # Fine Management (Staff)
    path("staff_add_fine/", views.staff_add_fine, name="staff_add_fine"),
    path("staff_add_fine_save/", views.staff_add_fine_save, name="staff_add_fine_save"),
    path("staff_manage_fines/", views.staff_manage_fines, name="staff_manage_fines"),
    path("staff_edit_fine/<fine_id>/", views.staff_edit_fine, name="staff_edit_fine"),
    path(
        "staff_edit_fine_save/", views.staff_edit_fine_save, name="staff_edit_fine_save"
    ),
    path(
        "staff_delete_fine/<fine_id>/",
        views.staff_delete_fine,
        name="staff_delete_fine",
    ),
    # Student URLs
    path("student_home/", views.student_home, name="student_home"),
    path(
        "student_view_attendance/",
        views.student_view_attendance,
        name="student_view_attendance",
    ),
    path(
        "student_view_attendance_post/",
        views.student_view_attendance_post,
        name="student_view_attendance_post",
    ),
    path("student_apply_leave/", views.student_apply_leave, name="student_apply_leave"),
    path(
        "student_apply_leave_save/",
        views.student_apply_leave_save,
        name="student_apply_leave_save",
    ),
    path("student_feedback/", views.student_feedback, name="student_feedback"),
    path(
        "student_feedback_save/",
        views.student_feedback_save,
        name="student_feedback_save",
    ),
    path("student_profile/", views.student_profile, name="student_profile"),
    path(
        "student_profile_update/",
        views.student_profile_update,
        name="student_profile_update",
    ),
    path("student_view_result/", views.student_view_result, name="student_view_result"),
    # Fine Management (Student)
    path("student_view_fines/", views.student_view_fines, name="student_view_fines"),
    path(
        "student_pay_fine/<fine_id>/", views.student_pay_fine, name="student_pay_fine"
    ),
    path(
        "student_pay_fine_save/",
        views.student_pay_fine_save,
        name="student_pay_fine_save",
    ),
    # AJAX URLs
    path("get_students/", views.get_students, name="get_students"),
    path(
        "save_attendance_data/", views.save_attendance_data, name="save_attendance_data"
    ),
    path(
        "get_attendance_dates/", views.get_attendance_dates, name="get_attendance_dates"
    ),
    path(
        "get_attendance_student/",
        views.get_attendance_student,
        name="get_attendance_student",
    ),
    path(
        "update_attendance_data/",
        views.update_attendance_data,
        name="update_attendance_data",
    ),
    # Health check
    path("health/", views.health_check, name="health_check"),
    # Debug endpoints
    path("debug-session/", views.debug_session, name="debug_session"),
]
