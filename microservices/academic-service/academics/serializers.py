from rest_framework import serializers

from .models import Course, Enrollment, SessionYear, Subject, SubjectEnrollment


class SessionYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = SessionYear
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")

    def validate(self, data):
        if data["start_date"] >= data["end_date"]:
            raise serializers.ValidationError("End date must be after start date")
        return data


class CourseSerializer(serializers.ModelSerializer):
    subjects_count = serializers.SerializerMethodField()
    enrollments_count = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")

    def get_subjects_count(self, obj):
        return obj.subjects.filter(is_active=True).count()

    def get_enrollments_count(self, obj):
        return obj.enrollments.filter(status="active").count()


class SubjectSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source="course.name", read_only=True)
    course_code = serializers.CharField(source="course.code", read_only=True)
    enrollments_count = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")

    def get_enrollments_count(self, obj):
        return obj.enrollments.filter(status="enrolled").count()


class EnrollmentSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source="course.name", read_only=True)
    course_code = serializers.CharField(source="course.code", read_only=True)
    session_name = serializers.CharField(source="session_year.name", read_only=True)
    subjects_enrolled = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at", "enrollment_date")

    def get_subjects_enrolled(self, obj):
        return obj.subject_enrollments.filter(status="enrolled").count()

    def validate(self, data):
        # Check if student is already enrolled in the same course and session
        if Enrollment.objects.filter(
            student_id=data["student_id"],
            course=data["course"],
            session_year=data["session_year"],
        ).exists():
            raise serializers.ValidationError(
                "Student is already enrolled in this course for the selected session"
            )
        return data


class SubjectEnrollmentSerializer(serializers.ModelSerializer):
    student_id = serializers.IntegerField(
        source="enrollment.student_id", read_only=True
    )
    course_name = serializers.CharField(source="enrollment.course.name", read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    subject_code = serializers.CharField(source="subject.code", read_only=True)
    subject_credits = serializers.IntegerField(source="subject.credits", read_only=True)

    class Meta:
        model = SubjectEnrollment
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at", "enrollment_date")

    def validate(self, data):
        # Check if student is already enrolled in the subject
        if SubjectEnrollment.objects.filter(
            enrollment=data["enrollment"], subject=data["subject"]
        ).exists():
            raise serializers.ValidationError(
                "Student is already enrolled in this subject"
            )

        # Check if subject belongs to the enrolled course
        if data["subject"].course != data["enrollment"].course:
            raise serializers.ValidationError(
                "Subject does not belong to the enrolled course"
            )

        return data


class CourseDetailSerializer(CourseSerializer):
    """Detailed course serializer with subjects"""

    subjects = SubjectSerializer(many=True, read_only=True)
    active_subjects = serializers.SerializerMethodField()

    class Meta(CourseSerializer.Meta):
        fields = [
            "id",
            "name",
            "code",
            "description",
            "duration_years",
            "is_active",
            "created_at",
            "updated_at",
            "subjects_count",
            "enrollments_count",
            "subjects",
            "active_subjects",
        ]

    def get_active_subjects(self, obj):
        return SubjectSerializer(obj.subjects.filter(is_active=True), many=True).data


class EnrollmentDetailSerializer(EnrollmentSerializer):
    """Detailed enrollment serializer with subject enrollments"""

    subject_enrollments = SubjectEnrollmentSerializer(many=True, read_only=True)
    course_details = CourseSerializer(source="course", read_only=True)

    class Meta(EnrollmentSerializer.Meta):
        fields = [
            "id",
            "student_id",
            "course",
            "session_year",
            "status",
            "enrollment_date",
            "created_at",
            "updated_at",
            "course_name",
            "course_code",
            "session_name",
            "subjects_enrolled",
            "subject_enrollments",
            "course_details",
        ]
