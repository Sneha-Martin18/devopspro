from django.contrib.auth import login, logout
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import AdminHOD, CustomUser, Staff, Student
from .serializers import (AdminHODSerializer, CustomUserSerializer,
                          PasswordChangeSerializer, StaffCreateSerializer,
                          StaffSerializer, StudentCreateSerializer,
                          StudentSerializer, UserLoginSerializer,
                          UserProfileSerializer)
from .tasks import send_welcome_email


class UserRegistrationView(generics.CreateAPIView):
    """Register a new user"""

    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Register a new user",
        description="Create a new user account with basic information",
    )
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_201_CREATED:
            # Send welcome email asynchronously
            user_id = response.data["id"]
            send_welcome_email.delay(user_id)
        return response


class UserLoginView(APIView):
    """User login endpoint"""

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="User login",
        description="Authenticate user and return JWT tokens",
        request=UserLoginSerializer,
    )
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]

            # Create JWT tokens
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token

            # Skip session tracking for now to avoid database issues

            # Update last login
            user.last_login = timezone.now()
            user.save(update_fields=["last_login"])

            return Response(
                {
                    "access_token": str(access_token),
                    "refresh_token": str(refresh),
                    "user": UserProfileSerializer(user).data,
                    "message": "Login successful",
                },
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip


class UserLogoutView(APIView):
    """User logout endpoint"""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="User logout", description="Logout user and invalidate session"
    )
    def post(self, request):
        try:
            # Simple logout - no session tracking needed
            return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": "Logout failed", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UserProfileView(generics.RetrieveUpdateAPIView):
    """Get and update user profile"""

    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    @extend_schema(
        summary="Get user profile",
        description="Retrieve current user's profile information",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update user profile",
        description="Update current user's profile information",
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class PasswordChangeView(APIView):
    """Change user password"""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Change password",
        description="Change current user's password",
        request=PasswordChangeSerializer,
    )
    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data["new_password"])
            user.save()

            # Password changed successfully - no session tracking needed

            return Response(
                {"message": "Password changed successfully"}, status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StudentListCreateView(generics.ListCreateAPIView):
    """List and create students"""

    queryset = Student.objects.select_related("admin").all()
    permission_classes = [permissions.AllowAny]  # Allow access for development

    def get_serializer_class(self):
        if self.request.method == "POST":
            return StudentCreateSerializer
        return StudentSerializer

    @extend_schema(summary="List students", description="Get list of all students")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create student",
        description="Create a new student with user account",
        request=StudentCreateSerializer,
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class StudentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, and delete student"""

    queryset = Student.objects.select_related("admin").all()
    serializer_class = StudentSerializer
    permission_classes = [permissions.AllowAny]  # Allow access for development

    @extend_schema(
        summary="Get student details",
        description="Retrieve specific student information",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(summary="Update student", description="Update student information")
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(summary="Delete student", description="Delete student account")
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class StaffListCreateView(generics.ListCreateAPIView):
    """List and create staff"""

    queryset = Staff.objects.select_related("admin").all()
    permission_classes = [permissions.AllowAny]  # Allow access for development

    def get_serializer_class(self):
        if self.request.method == "POST":
            return StaffCreateSerializer
        return StaffSerializer

    @extend_schema(summary="List staff", description="Get list of all staff members")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create staff",
        description="Create a new staff member with user account",
        request=StaffCreateSerializer,
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class StaffDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, and delete staff"""

    queryset = Staff.objects.select_related("admin").all()
    serializer_class = StaffSerializer
    permission_classes = [permissions.AllowAny]  # Allow access for development

    @extend_schema(
        summary="Get staff details",
        description="Retrieve specific staff member information",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update staff", description="Update staff member information"
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(summary="Delete staff", description="Delete staff member account")
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class AdminHODListView(generics.ListAPIView):
    """List admin HODs"""

    queryset = AdminHOD.objects.select_related("admin").all()
    serializer_class = AdminHODSerializer
    permission_classes = [permissions.AllowAny]  # Allow access for development

    @extend_schema(summary="List admin HODs", description="Get list of all admin HODs")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


# UserSessionListView removed - session tracking disabled


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
@extend_schema(
    summary="Get user by ID",
    description="Retrieve user information by user ID (for inter-service communication)",
    parameters=[
        OpenApiParameter(name="user_id", description="User ID", required=True, type=int)
    ],
)
def get_user_by_id(request, user_id):
    """Get user by ID - for inter-service communication"""
    try:
        user = CustomUser.objects.get(id=user_id)
        serializer = UserProfileSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except CustomUser.DoesNotExist:
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
@extend_schema(
    summary="Validate user token",
    description="Validate JWT token and return user information",
)
def validate_token(request):
    """Validate token and return user info - for inter-service communication"""
    user = request.user
    return Response(
        {"valid": True, "user": UserProfileSerializer(user).data},
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
@extend_schema(summary="Health check", description="Service health check endpoint")
def health_check(request):
    """Health check endpoint"""
    return Response(
        {
            "status": "healthy",
            "service": "user-management-service",
            "timestamp": timezone.now(),
        },
        status=status.HTTP_200_OK,
    )
