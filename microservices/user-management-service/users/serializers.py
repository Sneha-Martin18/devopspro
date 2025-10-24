from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import AdminHOD, CustomUser, Staff, Student


class CustomUserSerializer(serializers.ModelSerializer):
    """Serializer for CustomUser model"""

    password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "user_type",
            "is_active",
            "date_joined",
            "created_at",
            "updated_at",
            "password",
            "confirm_password",
        ]
        read_only_fields = ["id", "date_joined", "created_at", "updated_at"]

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError("Passwords don't match")
        return attrs

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        password = validated_data.pop("password")
        user = CustomUser.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login"""

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs.get("username")
        password = attrs.get("password")

        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError("Invalid credentials")
            if not user.is_active:
                raise serializers.ValidationError("User account is disabled")
            attrs["user"] = user
        else:
            raise serializers.ValidationError("Must include username and password")

        return attrs


class AdminHODSerializer(serializers.ModelSerializer):
    """Serializer for AdminHOD profile"""

    admin = CustomUserSerializer(read_only=True)

    class Meta:
        model = AdminHOD
        fields = [
            "id",
            "admin",
            "department",
            "phone_number",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class StaffSerializer(serializers.ModelSerializer):
    """Serializer for Staff profile"""

    admin = CustomUserSerializer(read_only=True)

    class Meta:
        model = Staff
        fields = [
            "id",
            "admin",
            "address",
            "phone_number",
            "employee_id",
            "department",
            "designation",
            "date_of_joining",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class StudentSerializer(serializers.ModelSerializer):
    """Serializer for Student profile"""

    admin = CustomUserSerializer(read_only=True)

    class Meta:
        model = Student
        fields = [
            "id",
            "admin",
            "gender",
            "profile_pic",
            "address",
            "phone_number",
            "student_id",
            "date_of_birth",
            "guardian_name",
            "guardian_phone",
            "course_id",
            "session_year_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class StudentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating student with user account"""

    admin = CustomUserSerializer()

    class Meta:
        model = Student
        fields = [
            "admin",
            "gender",
            "profile_pic",
            "address",
            "phone_number",
            "student_id",
            "date_of_birth",
            "guardian_name",
            "guardian_phone",
            "course_id",
            "session_year_id",
        ]

    def create(self, validated_data):
        admin_data = validated_data.pop("admin")
        admin_data["user_type"] = 3  # Student type

        # Create user account
        user_serializer = CustomUserSerializer(data=admin_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()

        # Create student profile
        student = Student.objects.create(admin=user, **validated_data)
        return student


class StaffCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating staff with user account"""

    admin = CustomUserSerializer()

    class Meta:
        model = Staff
        fields = [
            "admin",
            "address",
            "phone_number",
            "employee_id",
            "department",
            "designation",
            "date_of_joining",
        ]

    def create(self, validated_data):
        admin_data = validated_data.pop("admin")
        admin_data["user_type"] = 2  # Staff type

        # Create user account
        user_serializer = CustomUserSerializer(data=admin_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()

        # Create staff profile
        staff = Staff.objects.create(admin=user, **validated_data)
        return staff


# UserSessionSerializer removed - session tracking disabled


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change"""

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(
        write_only=True, validators=[validate_password]
    )
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError("New passwords don't match")
        return attrs

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value


class UserProfileSerializer(serializers.ModelSerializer):
    """Unified serializer for user profile based on user type"""

    profile = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "user_type",
            "is_active",
            "date_joined",
            "profile",
        ]
        read_only_fields = ["id", "username", "user_type", "date_joined"]

    def get_profile(self, obj):
        """Get profile data based on user type"""
        if obj.user_type == 1 and hasattr(obj, "admin_profile"):
            return AdminHODSerializer(obj.admin_profile).data
        elif obj.user_type == 2 and hasattr(obj, "staff_profile"):
            return StaffSerializer(obj.staff_profile).data
        elif obj.user_type == 3 and hasattr(obj, "student_profile"):
            return StudentSerializer(obj.student_profile).data
        return None
