from django import forms


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
    course_id = forms.ChoiceField(
        label="Course",
        choices=[],
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    session_year_id = forms.ChoiceField(
        label="Session Year",
        choices=[],
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    def __init__(self, *args, **kwargs):
        courses = kwargs.pop('courses', [])
        sessions = kwargs.pop('sessions', [])
        super(AddStudentForm, self).__init__(*args, **kwargs)
        
        # Populate course choices
        course_list = [(course.get('id'), course.get('course_name')) for course in courses]
        self.fields['course_id'].choices = course_list
        
        # Populate session choices
        session_list = [
            (session.get('id'), f"{session.get('session_start_year')} to {session.get('session_end_year')}")
            for session in sessions
        ]
        self.fields['session_year_id'].choices = session_list
