from datetime import datetime, timedelta

import requests
from django.conf import settings
from django.db.models import Avg, Count, Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (LeaveApproval, LeaveBalance, LeavePolicy, LeaveRequest,
                     LeaveType)
from .serializers import (BulkLeaveRequestSerializer,
                          LeaveApprovalCreateSerializer,
                          LeaveApprovalSerializer, LeaveBalanceSerializer,
                          LeavePolicySerializer, LeaveRequestCreateSerializer,
                          LeaveRequestSerializer, LeaveRequestUpdateSerializer,
                          LeaveStatsSerializer, LeaveTypeSerializer,
                          UserLeaveHistorySerializer)
from .tasks import process_leave_approval, send_leave_notification


class LeaveTypeViewSet(viewsets.ModelViewSet):
    """ViewSet for managing leave types"""

    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["category", "applicable_to", "is_active"]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at", "max_days_per_request"]
    ordering = ["name"]

    @action(detail=False, methods=["get"])
    def active(self, request):
        """Get only active leave types"""
        active_types = self.queryset.filter(is_active=True)
        serializer = self.get_serializer(active_types, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def by_user_type(self, request):
        """Get leave types filtered by user type"""
        user_type = request.query_params.get("user_type", "BOTH")
        leave_types = self.queryset.filter(
            Q(applicable_to=user_type) | Q(applicable_to="BOTH"), is_active=True
        )
        serializer = self.get_serializer(leave_types, many=True)
        return Response(serializer.data)


class LeaveRequestViewSet(viewsets.ModelViewSet):
    """ViewSet for managing leave requests"""

    queryset = LeaveRequest.objects.select_related("leave_type").all()
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["status", "user_type", "leave_type", "priority", "user_id"]
    search_fields = ["user_name", "reason", "user_email"]
    ordering_fields = ["created_at", "start_date", "end_date", "total_days"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "create":
            return LeaveRequestCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return LeaveRequestUpdateSerializer
        return LeaveRequestSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by date range
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        if start_date:
            queryset = queryset.filter(start_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(end_date__lte=end_date)

        return queryset

    def perform_create(self, serializer):
        leave_request = serializer.save()

        # Send notification asynchronously
        send_leave_notification.delay(
            leave_request.id, "SUBMITTED", leave_request.user_email
        )

    def perform_update(self, serializer):
        old_status = self.get_object().status
        leave_request = serializer.save()

        # Create approval record if status changed
        if old_status != leave_request.status:
            LeaveApproval.objects.create(
                leave_request=leave_request,
                approver_id=leave_request.approver_id or "system",
                approver_name=leave_request.approver_name or "System",
                approver_type="SYSTEM",
                action=leave_request.status,
                previous_status=old_status,
                new_status=leave_request.status,
            )

            # Update approved_at timestamp
            if leave_request.status == "APPROVED":
                leave_request.approved_at = timezone.now()
                leave_request.save()

            # Send notification
            send_leave_notification.delay(
                leave_request.id, leave_request.status, leave_request.user_email
            )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve a leave request"""
        leave_request = self.get_object()

        if leave_request.status != "PENDING":
            return Response(
                {"error": "Only pending requests can be approved"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        approver_data = request.data
        leave_request.status = "APPROVED"
        leave_request.approver_id = approver_data.get("approver_id", "")
        leave_request.approver_name = approver_data.get("approver_name", "")
        leave_request.approved_at = timezone.now()
        leave_request.save()

        # Create approval record
        LeaveApproval.objects.create(
            leave_request=leave_request,
            approver_id=leave_request.approver_id,
            approver_name=leave_request.approver_name,
            approver_type=approver_data.get("approver_type", "STAFF"),
            action="APPROVED",
            comments=approver_data.get("comments", ""),
            previous_status="PENDING",
            new_status="APPROVED",
        )

        # Process approval (update balances, send notifications)
        process_leave_approval.delay(leave_request.id, "APPROVED")

        serializer = self.get_serializer(leave_request)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Reject a leave request"""
        leave_request = self.get_object()

        if leave_request.status != "PENDING":
            return Response(
                {"error": "Only pending requests can be rejected"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        approver_data = request.data
        leave_request.status = "REJECTED"
        leave_request.approver_id = approver_data.get("approver_id", "")
        leave_request.approver_name = approver_data.get("approver_name", "")
        leave_request.rejection_reason = approver_data.get("rejection_reason", "")
        leave_request.save()

        # Create approval record
        LeaveApproval.objects.create(
            leave_request=leave_request,
            approver_id=leave_request.approver_id,
            approver_name=leave_request.approver_name,
            approver_type=approver_data.get("approver_type", "STAFF"),
            action="REJECTED",
            comments=approver_data.get("comments", ""),
            previous_status="PENDING",
            new_status="REJECTED",
        )

        # Send notification
        send_leave_notification.delay(
            leave_request.id, "REJECTED", leave_request.user_email
        )

        serializer = self.get_serializer(leave_request)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel a leave request"""
        leave_request = self.get_object()

        if leave_request.status not in ["PENDING", "APPROVED"]:
            return Response(
                {"error": "Only pending or approved requests can be cancelled"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = leave_request.status
        leave_request.status = "CANCELLED"
        leave_request.save()

        # Create approval record
        LeaveApproval.objects.create(
            leave_request=leave_request,
            approver_id=request.data.get("user_id", ""),
            approver_name=request.data.get("user_name", ""),
            approver_type="USER",
            action="CANCELLED",
            comments=request.data.get("reason", ""),
            previous_status=old_status,
            new_status="CANCELLED",
        )

        # Process cancellation (update balances if was approved)
        if old_status == "APPROVED":
            process_leave_approval.delay(leave_request.id, "CANCELLED")

        serializer = self.get_serializer(leave_request)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def my_requests(self, request):
        """Get current user's leave requests"""
        user_id = request.query_params.get("user_id")
        if not user_id:
            return Response(
                {"error": "user_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        requests = self.queryset.filter(user_id=user_id)
        page = self.paginate_queryset(requests)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(requests, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def pending_approvals(self, request):
        """Get pending leave requests for approval"""
        approver_id = request.query_params.get("approver_id")
        if not approver_id:
            return Response(
                {"error": "approver_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pending_requests = self.queryset.filter(status="PENDING")
        page = self.paginate_queryset(pending_requests)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(pending_requests, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def current_leaves(self, request):
        """Get currently active leaves"""
        today = timezone.now().date()
        current_leaves = self.queryset.filter(
            status="APPROVED", start_date__lte=today, end_date__gte=today
        )

        serializer = self.get_serializer(current_leaves, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def bulk_create(self, request):
        """Create multiple leave requests"""
        serializer = BulkLeaveRequestSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            created_requests = []

            for user_id in data["user_ids"]:
                # You would fetch user details from User Management Service here
                leave_request = LeaveRequest.objects.create(
                    user_id=user_id,
                    user_type=request.data.get("user_type", "STUDENT"),
                    user_name=f"User {user_id}",  # Fetch from user service
                    user_email=f"user{user_id}@example.com",  # Fetch from user service
                    leave_type=data["leave_type"],
                    start_date=data["start_date"],
                    end_date=data["end_date"],
                    reason=data["reason"],
                    priority=data["priority"],
                )
                created_requests.append(leave_request)

            response_serializer = LeaveRequestSerializer(created_requests, many=True)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Get leave statistics"""
        # Basic stats
        total_requests = self.queryset.count()
        pending_requests = self.queryset.filter(status="PENDING").count()
        approved_requests = self.queryset.filter(status="APPROVED").count()
        rejected_requests = self.queryset.filter(status="REJECTED").count()

        today = timezone.now().date()
        current_leaves = self.queryset.filter(
            status="APPROVED", start_date__lte=today, end_date__gte=today
        ).count()

        upcoming_leaves = self.queryset.filter(
            status="APPROVED", start_date__gt=today
        ).count()

        # Stats by leave type
        by_leave_type = dict(
            self.queryset.values("leave_type__name")
            .annotate(count=Count("id"))
            .values_list("leave_type__name", "count")
        )

        # Stats by month (current year)
        current_year = timezone.now().year
        by_month = {}
        for month in range(1, 13):
            month_count = self.queryset.filter(
                created_at__year=current_year, created_at__month=month
            ).count()
            by_month[f"{current_year}-{month:02d}"] = month_count

        # Average processing time
        processed_requests = self.queryset.filter(
            status__in=["APPROVED", "REJECTED"]
        ).exclude(approved_at__isnull=True)

        avg_processing_days = 0
        if processed_requests.exists():
            avg_processing_days = processed_requests.aggregate(
                avg_days=Avg("approved_at") - Avg("created_at")
            )["avg_days"]
            if avg_processing_days:
                avg_processing_days = avg_processing_days.days

        stats_data = {
            "total_requests": total_requests,
            "pending_requests": pending_requests,
            "approved_requests": approved_requests,
            "rejected_requests": rejected_requests,
            "current_leaves": current_leaves,
            "upcoming_leaves": upcoming_leaves,
            "by_leave_type": by_leave_type,
            "by_month": by_month,
            "avg_processing_days": avg_processing_days or 0,
        }

        serializer = LeaveStatsSerializer(stats_data)
        return Response(serializer.data)


class LeaveBalanceViewSet(viewsets.ModelViewSet):
    """ViewSet for managing leave balances"""

    queryset = LeaveBalance.objects.select_related("leave_type").all()
    serializer_class = LeaveBalanceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["user_id", "user_type", "leave_type", "year"]
    ordering_fields = ["year", "total_allocated", "used_days"]
    ordering = ["-year", "leave_type__name"]

    @action(detail=False, methods=["get"])
    def user_balances(self, request):
        """Get leave balances for a specific user"""
        user_id = request.query_params.get("user_id")
        year = request.query_params.get("year", timezone.now().year)

        if not user_id:
            return Response(
                {"error": "user_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        balances = self.queryset.filter(user_id=user_id, year=year)
        serializer = self.get_serializer(balances, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def initialize_balances(self, request):
        """Initialize leave balances for users"""
        user_ids = request.data.get("user_ids", [])
        year = request.data.get("year", timezone.now().year)

        if not user_ids:
            return Response(
                {"error": "user_ids list is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_balances = []
        for user_id in user_ids:
            for leave_type in LeaveType.objects.filter(is_active=True):
                balance, created = LeaveBalance.objects.get_or_create(
                    user_id=user_id,
                    leave_type=leave_type,
                    year=year,
                    defaults={
                        "user_type": request.data.get("user_type", "STUDENT"),
                        "total_allocated": leave_type.max_days_per_year,
                    },
                )
                if created:
                    created_balances.append(balance)

        serializer = self.get_serializer(created_balances, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class LeaveApprovalViewSet(viewsets.ModelViewSet):
    """ViewSet for managing leave approvals"""

    queryset = LeaveApproval.objects.select_related("leave_request").all()
    serializer_class = LeaveApprovalSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["leave_request", "approver_id", "action"]
    ordering_fields = ["action_date"]
    ordering = ["-action_date"]

    def get_serializer_class(self):
        if self.action == "create":
            return LeaveApprovalCreateSerializer
        return LeaveApprovalSerializer

    @action(detail=False, methods=["get"])
    def by_approver(self, request):
        """Get approvals by a specific approver"""
        approver_id = request.query_params.get("approver_id")
        if not approver_id:
            return Response(
                {"error": "approver_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        approvals = self.queryset.filter(approver_id=approver_id)
        page = self.paginate_queryset(approvals)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(approvals, many=True)
        return Response(serializer.data)


class LeavePolicyViewSet(viewsets.ModelViewSet):
    """ViewSet for managing leave policies"""

    queryset = LeavePolicy.objects.all()
    serializer_class = LeavePolicySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["policy_type", "user_type", "is_active", "leave_type"]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "effective_from", "created_at"]
    ordering = ["name"]

    @action(detail=False, methods=["get"])
    def active_policies(self, request):
        """Get currently active policies"""
        today = timezone.now().date()
        active_policies = self.queryset.filter(
            is_active=True, effective_from__lte=today
        ).filter(Q(effective_to__isnull=True) | Q(effective_to__gte=today))

        serializer = self.get_serializer(active_policies, many=True)
        return Response(serializer.data)
