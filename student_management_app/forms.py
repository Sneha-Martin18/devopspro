from django import forms
from django.forms import Form

from student_management_app.models import Courses, SessionYearModel, Students


class DateInput(forms.DateInput):
    input_type = "date"


class AddStudentForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        max_length=50,
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )
    password = forms.CharField(
        label="Password",
        max_length=50,
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    first_name = forms.CharField(
        label="First Name",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_name = forms.CharField(
        label="Last Name",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    username = forms.CharField(
        label="Username",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    address = forms.CharField(
        label="Address",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    gender_list = (("Male", "Male"), ("Female", "Female"))
    gender = forms.ChoiceField(
        label="Gender",
        choices=gender_list,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    profile_pic = forms.FileField(
        label="Profile Pic",
        required=False,
        widget=forms.FileInput(attrs={"class": "form-control"}),
    )

    # For course selection
    try:
        courses = Courses.objects.all()
        course_list = []
        for course in courses:
            course_list.append((course.id, course.course_name))
    except:
        course_list = []

    course_id = forms.ChoiceField(
        label="Course",
        choices=course_list,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    # For session years
    try:
        session_years = SessionYearModel.objects.all()
        session_list = []
        for session in session_years:
            session_list.append(
                (
                    session.id,
                    f"{session.session_start_year} to {session.session_end_year}",
                )
            )
    except:
        session_list = []

    session_year_id = forms.ChoiceField(
        label="Session Year",
        choices=session_list,
        widget=forms.Select(attrs={"class": "form-control"}),
    )


class EditStudentForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        max_length=50,
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )
    first_name = forms.CharField(
        label="First Name",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_name = forms.CharField(
        label="Last Name",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    username = forms.CharField(
        label="Username",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    address = forms.CharField(
        label="Address",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    # For Displaying Courses
    try:
        courses = Courses.objects.all()
        course_list = []
        for course in courses:
            single_course = (course.id, course.course_name)
            course_list.append(single_course)
    except:
        course_list = []

    # For Displaying Session Years
    try:
        session_years = SessionYearModel.objects.all()
        session_year_list = []
        for session_year in session_years:
            single_session_year = (
                session_year.id,
                str(session_year.session_start_year)
                + " to "
                + str(session_year.session_end_year),
            )
            session_year_list.append(single_session_year)

    except:
        session_year_list = []

    gender_list = (("Male", "Male"), ("Female", "Female"))

    course_id = forms.ChoiceField(
        label="Course",
        choices=course_list,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    gender = forms.ChoiceField(
        label="Gender",
        choices=gender_list,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    session_year_id = forms.ChoiceField(
        label="Session Year",
        choices=session_year_list,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    # session_start_year = forms.DateField(label="Session Start", widget=DateInput(attrs={"class":"form-control"}))
    # session_end_year = forms.DateField(label="Session End", widget=DateInput(attrs={"class":"form-control"}))
    profile_pic = forms.FileField(
        label="Profile Pic",
        required=False,
        widget=forms.FileInput(attrs={"class": "form-control"}),
    )


class AddFineForm(forms.Form):
    student_id = forms.ChoiceField(
        label="Student",
        choices=[],
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    amount = forms.DecimalField(
        label="Fine Amount",
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    reason = forms.CharField(
        label="Reason",
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    due_date = forms.DateField(
        label="Due Date", widget=DateInput(attrs={"class": "form-control"})
    )

    def __init__(self, *args, **kwargs):
        super(AddFineForm, self).__init__(*args, **kwargs)
        try:
            students = Students.objects.all()
            self.fields["student_id"].choices = [
                (
                    str(student.admin.id),
                    f"{student.admin.first_name} {student.admin.last_name} - {student.course_id.course_name}",
                )
                for student in students
            ]
        except Exception as e:
            print(f"Error loading students: {str(e)}")
            self.fields["student_id"].choices = []
