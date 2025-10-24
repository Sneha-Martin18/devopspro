from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from .models import (LeaveApproval, LeaveBalance, LeavePolicy, LeaveRequest,
                     LeaveType)


class LeaveTypeSerializer(serializers.ModelSerializer):
    """Serializer for LeaveType model"""

    class Meta:
        model = LeaveType
        fields = [
            "id",
            "name",
            "category",
            "description",
            "applicable_to",
            "max_days_per_request",
            "max_days_per_year",
            "requires_approval",
            "advance_notice_days",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_max_days_per_request(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Maximum days per request must be greater than 0"
            )
        if value > 365:
            raise serializers.ValidationError(
                "Maximum days per request cannot exceed 365 days"
            )
        return value


class LeaveRequestSerializer(serializers.ModelSerializer):
    """Serializer for LeaveRequest model"""

    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    leave_type_category = serializers.CharField(
        source="leave_type.category", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    priority_display = serializers.CharField(
        source="get_priority_display", read_only=True
    )
    is_current = serializers.BooleanField(read_only=True)
    is_upcoming = serializers.BooleanField(read_only=True)
    days_until_start = serializers.IntegerField(read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "user_id",
            "user_type",
            "user_name",
            "user_email",
            "leave_type",
            "leave_type_name",
            "leave_type_category",
            "start_date",
            "end_date",
            "total_days",
            "reason",
            "emergency_contact",
            "attachment",
            "status",
            "status_display",
            "priority",
            "priority_display",
            "approver_id",
            "approver_name",
            "approved_at",
            "rejection_reason",
            "created_at",
            "updated_at",
            "submitted_at",
            "academic_year",
            "semester",
            "is_current",
            "is_upcoming",
            "days_until_start",
        ]
        read_only_fields = [
            "id",
            "total_days",
            "approver_id",
            "approver_name",
            "approved_at",
            "created_at",
            "updated_at",
            "submitted_at",
        ]

    def validate(self, data):
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        leave_type = data.get("leave_type")

        if start_date and end_date:
            if start_date > end_date:
                raise serializers.ValidationError("Start date cannot be after end date")

            if start_date < timezone.now().date():
                raise serializers.ValidationError("Cannot request leave for past dates")

            # Calculate total days
            total_days = (end_date - start_date).days + 1
            data["total_days"] = total_days

            # Validate against leave type constraints
            if leave_type:
                if total_days > leave_type.max_days_per_request:
                    raise serializers.ValidationError(
                        f"Leave request exceeds maximum allowed days ({leave_type.max_days_per_request}) for {leave_type.name}"
                    )

                # Check advance notice requirement
                if leave_type.advance_notice_days > 0:
                    notice_date = timezone.now().date() + timedelta(
                        days=leave_type.advance_notice_days
                    )
                    if start_date < notice_date:
                        raise serializers.ValidationError(
                            f"Leave must be requested at least {leave_type.advance_notice_days} days in advance"
                        )

        return data

    def validate_leave_type(self, value):
        if not value.is_active:
            raise serializers.ValidationError("Selected leave type is not active")
        return value


class LeaveRequestCreateSerializer(LeaveRequestSerializer):
    """Serializer for creating leave requests"""

    class Meta(LeaveRequestSerializer.Meta):
        fields = [
            "user_id",
            "user_type",
            "user_name",
            "user_email",
            "leave_type",
            "start_date",
            "end_date",
            "reason",
            "emergency_contact",
            "attachment",
            "priority",
            "academic_year",
            "semester",
        ]


class LeaveRequestUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating leave request status"""

    class Meta:
        model = LeaveRequest
        fields = ["status", "rejection_reason", "approver_id", "approver_name"]

    def validate_status(self, value):
        instance = self.instance
        if (
            instance
            and instance.status in ["APPROVED", "REJECTED"]
            and value != instance.status
        ):
            raise serializers.ValidationError(
                "Cannot modify already processed leave request"
            )
        return value


class LeaveBalanceSerializer(serializers.ModelSerializer):
    """Serializer for LeaveBalance model"""

    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    available_days = serializers.IntegerField(read_only=True)
    utilization_percentage = serializers.FloatField(read_only=True)

    class Meta:
        model = LeaveBalance
        fields = [
            "id",
            "user_id",
            "user_type",
            "leave_type",
            "leave_type_name",
            "total_allocated",
            "used_days",
            "pending_days",
            "available_days",
            "utilization_percentage",
            "year",
            "academic_year",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class LeaveApprovalSerializer(serializers.ModelSerializer):
    """Serializer for LeaveApproval model"""

    leave_request_summary = serializers.SerializerMethodField()
    action_display = serializers.CharField(source="get_action_display", read_only=True)

    class Meta:
        model = LeaveApproval
        fields = [
            "id",
            "leave_request",
            "leave_request_summary",
            "approver_id",
            "approver_name",
            "approver_type",
            "action",
            "action_display",
            "comments",
            "action_date",
            "previous_status",
            "new_status",
        ]
        read_only_fields = ["id", "action_date"]

    def get_leave_request_summary(self, obj):
        return f"{obj.leave_request.user_name} - {obj.leave_request.leave_type.name}"


class LeaveApprovalCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating leave approvals"""

    class Meta:
        model = LeaveApproval
        fields = [
            "leave_request",
            "approver_id",
            "approver_name",
            "approver_type",
            "action",
            "comments",
            "previous_status",
            "new_status",
        ]


class LeavePolicySerializer(serializers.ModelSerializer):
    """Serializer for LeavePolicy model"""

    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    policy_type_display = serializers.CharField(
        source="get_policy_type_display", read_only=True
    )

    class Meta:
        model = LeavePolicy
        fields = [
            "id",
            "name",
            "policy_type",
            "policy_type_display",
            "description",
            "leave_type",
            "leave_type_name",
            "user_type",
            "rules",
            "is_active",
            "effective_from",
            "effective_to",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_effective_dates(self, data):
        effective_from = data.get("effective_from")
        effective_to = data.get("effective_to")

        if effective_from and effective_to:
            if effective_from >= effective_to:
                raise serializers.ValidationError(
                    "Effective from date must be before effective to date"
                )

        return data


class BulkLeaveRequestSerializer(serializers.Serializer):
    """Serializer for bulk leave request creation"""

    user_ids = serializers.ListField(
        child=serializers.CharField(max_length=100), min_length=1, max_length=100
    )
    leave_type = serializers.PrimaryKeyRelatedField(
        queryset=LeaveType.objects.filter(is_active=True)
    )
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField(max_length=1000)
    priority = serializers.ChoiceField(
        choices=LeaveRequest.PRIORITY_CHOICES, default="MEDIUM"
    )

    def validate(self, data):
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        if start_date and end_date:
            if start_date > end_date:
                raise serializers.ValidationError("Start date cannot be after end date")

            if start_date < timezone.now().date():
                raise serializers.ValidationError("Cannot request leave for past dates")

        return data


class LeaveStatsSerializer(serializers.Serializer):
    """Serializer for leave statistics"""

    total_requests = serializers.IntegerField()
    pending_requests = serializers.IntegerField()
    approved_requests = serializers.IntegerField()
    rejected_requests = serializers.IntegerField()
    current_leaves = serializers.IntegerField()
    upcoming_leaves = serializers.IntegerField()

    # By leave type
    by_leave_type = serializers.DictField()

    # By month
    by_month = serializers.DictField()

    # Average processing time
    avg_processing_days = serializers.FloatField()


class UserLeaveHistorySerializer(serializers.Serializer):
    """Serializer for user leave history"""

    user_id = serializers.CharField()
    user_name = serializers.CharField()
    total_leaves_taken = serializers.IntegerField()
    total_days_taken = serializers.IntegerField()
    current_year_leaves = serializers.IntegerField()
    pending_requests = serializers.IntegerField()

    # Recent requests
    recent_requests = LeaveRequestSerializer(many=True, read_only=True)

    # Leave balances
    leave_balances = LeaveBalanceSerializer(many=True, read_only=True)
