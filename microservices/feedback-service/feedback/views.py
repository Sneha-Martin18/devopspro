from datetime import datetime, timedelta

import requests
from django.conf import settings
from django.db.models import Avg, Count, F, Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (Feedback, FeedbackAnalytics, FeedbackCategory,
                     FeedbackResponse, FeedbackSurvey, FeedbackTemplate)
from .serializers import (BulkFeedbackSerializer, FeedbackAnalyticsSerializer,
                          FeedbackCategorySerializer, FeedbackCreateSerializer,
                          FeedbackModerationSerializer,
                          FeedbackResponseSerializer, FeedbackSerializer,
                          FeedbackStatsSerializer, FeedbackSurveySerializer,
                          FeedbackTemplateSerializer, FeedbackUpdateSerializer,
                          UserFeedbackHistorySerializer)
from .tasks import process_feedback_analytics, send_feedback_notification


class FeedbackCategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for managing feedback categories"""

    queryset = FeedbackCategory.objects.all()
    serializer_class = FeedbackCategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["category_type", "target_audience", "is_active"]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "display_order", "created_at"]
    ordering = ["display_order", "name"]

    @action(detail=False, methods=["get"])
    def active(self, request):
        """Get only active categories"""
        active_categories = self.queryset.filter(is_active=True)
        serializer = self.get_serializer(active_categories, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def by_audience(self, request):
        """Get categories filtered by target audience"""
        audience = request.query_params.get("audience", "BOTH")
        categories = self.queryset.filter(
            Q(target_audience=audience) | Q(target_audience="BOTH"), is_active=True
        )
        serializer = self.get_serializer(categories, many=True)
        return Response(serializer.data)


class FeedbackViewSet(viewsets.ModelViewSet):
    """ViewSet for managing feedback"""

    queryset = (
        Feedback.objects.select_related("category").prefetch_related("responses").all()
    )
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = [
        "status",
        "priority",
        "category",
        "rating",
        "user_type",
        "user_id",
        "target_type",
        "target_id",
        "is_public",
        "is_featured",
        "sentiment",
    ]
    search_fields = ["title", "description", "user_name", "target_name"]
    ordering_fields = ["created_at", "rating", "updated_at"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "create":
            return FeedbackCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return FeedbackUpdateSerializer
        return FeedbackSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by date range
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)

        # Filter by rating range
        min_rating = self.request.query_params.get("min_rating")
        max_rating = self.request.query_params.get("max_rating")

        if min_rating:
            queryset = queryset.filter(rating__gte=min_rating)
        if max_rating:
            queryset = queryset.filter(rating__lte=max_rating)

        return queryset

    def perform_create(self, serializer):
        feedback = serializer.save()

        # Send notification asynchronously
        send_feedback_notification.delay(
            feedback.id,
            "SUBMITTED",
            feedback.user_email if not feedback.is_anonymous else None,
        )

    def perform_update(self, serializer):
        old_status = self.get_object().status
        feedback = serializer.save()

        # Send notification if status changed
        if old_status != feedback.status:
            if feedback.status == "APPROVED":
                feedback.moderated_at = timezone.now()
                feedback.save()

            send_feedback_notification.delay(
                feedback.id,
                feedback.status,
                feedback.user_email if not feedback.is_anonymous else None,
            )

    @action(detail=True, methods=["post"])
    def moderate(self, request, pk=None):
        """Moderate feedback (approve/reject)"""
        feedback = self.get_object()
        action = request.data.get("action")  # 'approve' or 'reject'

        if action not in ["approve", "reject"]:
            return Response(
                {"error": 'Action must be "approve" or "reject"'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if feedback.status not in ["SUBMITTED", "UNDER_REVIEW"]:
            return Response(
                {"error": "Only submitted or under review feedback can be moderated"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        feedback.status = "APPROVED" if action == "approve" else "REJECTED"
        feedback.moderator_id = request.data.get("moderator_id", "")
        feedback.moderator_name = request.data.get("moderator_name", "")
        feedback.moderation_notes = request.data.get("moderation_notes", "")
        feedback.moderated_at = timezone.now()
        feedback.save()

        # Send notification
        send_feedback_notification.delay(
            feedback.id,
            feedback.status,
            feedback.user_email if not feedback.is_anonymous else None,
        )

        serializer = self.get_serializer(feedback)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def respond(self, request, pk=None):
        """Add response to feedback"""
        feedback = self.get_object()

        response_data = {
            "feedback": feedback.id,
            "responder_id": request.data.get("responder_id"),
            "responder_name": request.data.get("responder_name"),
            "responder_type": request.data.get("responder_type", "STAFF"),
            "responder_designation": request.data.get("responder_designation", ""),
            "response_type": request.data.get("response_type", "OFFICIAL"),
            "message": request.data.get("message"),
            "attachments": request.data.get("attachments", []),
            "is_public": request.data.get("is_public", True),
            "is_final": request.data.get("is_final", False),
        }

        response_serializer = FeedbackResponseSerializer(data=response_data)
        if response_serializer.is_valid():
            response_obj = response_serializer.save()

            # Update feedback status if final response
            if response_obj.is_final:
                feedback.status = "RESOLVED"
                feedback.save()

            # Send notification
            send_feedback_notification.delay(
                feedback.id,
                "RESPONSE_ADDED",
                feedback.user_email if not feedback.is_anonymous else None,
            )

            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        return Response(response_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"])
    def my_feedback(self, request):
        """Get current user's feedback"""
        user_id = request.query_params.get("user_id")
        if not user_id:
            return Response(
                {"error": "user_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        feedback = self.queryset.filter(user_id=user_id)
        page = self.paginate_queryset(feedback)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(feedback, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def pending_moderation(self, request):
        """Get feedback pending moderation"""
        pending_feedback = self.queryset.filter(
            status__in=["SUBMITTED", "UNDER_REVIEW"]
        )
        page = self.paginate_queryset(pending_feedback)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(pending_feedback, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def public_feedback(self, request):
        """Get public feedback"""
        public_feedback = self.queryset.filter(is_public=True, status="APPROVED")

        # Filter by category if specified
        category = request.query_params.get("category")
        if category:
            public_feedback = public_feedback.filter(category=category)

        page = self.paginate_queryset(public_feedback)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(public_feedback, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def featured(self, request):
        """Get featured feedback"""
        featured_feedback = self.queryset.filter(
            is_featured=True, is_public=True, status="APPROVED"
        )

        serializer = self.get_serializer(featured_feedback, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def bulk_create(self, request):
        """Create multiple feedback entries"""
        serializer = BulkFeedbackSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            created_feedback = []

            for user_id in data["user_ids"]:
                # You would fetch user details from User Management Service here
                feedback = Feedback.objects.create(
                    user_id=user_id,
                    user_type=request.data.get("user_type", "STUDENT"),
                    user_name=f"User {user_id}",  # Fetch from user service
                    user_email=f"user{user_id}@example.com",  # Fetch from user service
                    category=data["category"],
                    title=data["title"],
                    description=data["description"],
                    rating=data["rating"],
                    target_type=data.get("target_type", ""),
                    target_id=data.get("target_id", ""),
                    target_name=data.get("target_name", ""),
                    is_anonymous=data["is_anonymous"],
                    priority=data["priority"],
                )
                created_feedback.append(feedback)

            response_serializer = FeedbackSerializer(created_feedback, many=True)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def bulk_moderate(self, request):
        """Bulk moderate feedback"""
        serializer = FeedbackModerationSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            feedback_ids = data["feedback_ids"]
            action = data["action"]

            feedback_list = self.queryset.filter(id__in=feedback_ids)

            if action == "approve":
                feedback_list.update(
                    status="APPROVED",
                    moderator_id=data["moderator_id"],
                    moderator_name=data["moderator_name"],
                    moderation_notes=data.get("moderation_notes", ""),
                    moderated_at=timezone.now(),
                )
            elif action == "reject":
                feedback_list.update(
                    status="REJECTED",
                    moderator_id=data["moderator_id"],
                    moderator_name=data["moderator_name"],
                    moderation_notes=data.get("moderation_notes", ""),
                    moderated_at=timezone.now(),
                )
            elif action == "feature":
                feedback_list.update(is_featured=True)
            elif action == "unfeature":
                feedback_list.update(is_featured=False)

            return Response({"message": f"{len(feedback_list)} feedback items updated"})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Get feedback statistics"""
        # Basic stats
        total_feedback = self.queryset.count()
        pending_moderation = self.queryset.filter(
            status__in=["SUBMITTED", "UNDER_REVIEW"]
        ).count()
        approved_feedback = self.queryset.filter(status="APPROVED").count()
        rejected_feedback = self.queryset.filter(status="REJECTED").count()

        # Average rating
        avg_rating = (
            self.queryset.aggregate(avg_rating=Avg("rating"))["avg_rating"] or 0
        )

        # Stats by category
        by_category = dict(
            self.queryset.values("category__name")
            .annotate(count=Count("id"))
            .values_list("category__name", "count")
        )

        # Stats by rating
        by_rating = dict(
            self.queryset.values("rating")
            .annotate(count=Count("id"))
            .values_list("rating", "count")
        )

        # Stats by sentiment
        by_sentiment = dict(
            self.queryset.exclude(sentiment="")
            .values("sentiment")
            .annotate(count=Count("id"))
            .values_list("sentiment", "count")
        )

        # Stats by month (current year)
        current_year = timezone.now().year
        by_month = {}
        for month in range(1, 13):
            month_count = self.queryset.filter(
                created_at__year=current_year, created_at__month=month
            ).count()
            by_month[f"{current_year}-{month:02d}"] = month_count

        # Response metrics
        total_responses = FeedbackResponse.objects.count()
        response_rate = (
            (total_responses / total_feedback * 100) if total_feedback > 0 else 0
        )

        # Average response time (in hours)
        responded_feedback = self.queryset.filter(responses__isnull=False).distinct()
        avg_response_time = 0
        if responded_feedback.exists():
            # This is a simplified calculation
            avg_response_time = 24  # Placeholder

        stats_data = {
            "total_feedback": total_feedback,
            "pending_moderation": pending_moderation,
            "approved_feedback": approved_feedback,
            "rejected_feedback": rejected_feedback,
            "average_rating": round(avg_rating, 2),
            "by_category": by_category,
            "by_rating": by_rating,
            "by_sentiment": by_sentiment,
            "by_month": by_month,
            "response_rate": round(response_rate, 2),
            "avg_response_time": avg_response_time,
        }

        serializer = FeedbackStatsSerializer(stats_data)
        return Response(serializer.data)


class FeedbackResponseViewSet(viewsets.ModelViewSet):
    """ViewSet for managing feedback responses"""

    queryset = FeedbackResponse.objects.select_related("feedback").all()
    serializer_class = FeedbackResponseSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["feedback", "responder_id", "response_type", "is_public"]
    ordering_fields = ["created_at"]
    ordering = ["created_at"]

    @action(detail=False, methods=["get"])
    def by_responder(self, request):
        """Get responses by a specific responder"""
        responder_id = request.query_params.get("responder_id")
        if not responder_id:
            return Response(
                {"error": "responder_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        responses = self.queryset.filter(responder_id=responder_id)
        page = self.paginate_queryset(responses)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(responses, many=True)
        return Response(serializer.data)


class FeedbackTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for managing feedback templates"""

    queryset = FeedbackTemplate.objects.prefetch_related("categories").all()
    serializer_class = FeedbackTemplateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["template_type", "target_audience", "is_active", "is_mandatory"]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    @action(detail=False, methods=["get"])
    def active(self, request):
        """Get only active templates"""
        now = timezone.now()
        active_templates = (
            self.queryset.filter(is_active=True)
            .filter(Q(start_date__isnull=True) | Q(start_date__lte=now))
            .filter(Q(end_date__isnull=True) | Q(end_date__gte=now))
        )

        serializer = self.get_serializer(active_templates, many=True)
        return Response(serializer.data)


class FeedbackSurveyViewSet(viewsets.ModelViewSet):
    """ViewSet for managing feedback surveys"""

    queryset = FeedbackSurvey.objects.select_related("template").all()
    serializer_class = FeedbackSurveySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["status", "target_type", "target_audience", "created_by"]
    search_fields = ["title", "description", "target_name"]
    ordering_fields = ["created_at", "start_date", "end_date"]
    ordering = ["-created_at"]

    @action(detail=False, methods=["get"])
    def active(self, request):
        """Get currently active surveys"""
        now = timezone.now()
        active_surveys = self.queryset.filter(
            status="ACTIVE", start_date__lte=now, end_date__gte=now
        )

        serializer = self.get_serializer(active_surveys, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def launch(self, request, pk=None):
        """Launch a survey"""
        survey = self.get_object()

        if survey.status != "DRAFT":
            return Response(
                {"error": "Only draft surveys can be launched"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        survey.status = "ACTIVE"
        survey.total_participants = len(survey.participant_ids)
        survey.save()

        # Send survey invitations
        # This would integrate with notification service

        serializer = self.get_serializer(survey)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        """Pause a survey"""
        survey = self.get_object()

        if survey.status != "ACTIVE":
            return Response(
                {"error": "Only active surveys can be paused"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        survey.status = "PAUSED"
        survey.save()

        serializer = self.get_serializer(survey)
        return Response(serializer.data)


class FeedbackAnalyticsViewSet(viewsets.ModelViewSet):
    """ViewSet for managing feedback analytics"""

    queryset = FeedbackAnalytics.objects.all()
    serializer_class = FeedbackAnalyticsSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["report_type", "generated_by"]
    ordering_fields = ["generated_at", "start_date", "end_date"]
    ordering = ["-generated_at"]

    @action(detail=False, methods=["post"])
    def generate_report(self, request):
        """Generate analytics report"""
        report_data = request.data

        # Trigger analytics generation task
        task = process_feedback_analytics.delay(
            report_data.get("report_type", "CUSTOM"),
            report_data.get("start_date"),
            report_data.get("end_date"),
            report_data.get("categories", []),
            report_data.get("target_types", []),
            request.data.get("generated_by", "system"),
        )

        return Response(
            {"message": "Analytics report generation started", "task_id": task.id}
        )

    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        """Get dashboard analytics"""
        # Get recent analytics or generate basic stats
        recent_analytics = self.queryset.filter(
            report_type="DAILY", generated_at__gte=timezone.now() - timedelta(days=1)
        ).first()

        if recent_analytics:
            serializer = self.get_serializer(recent_analytics)
            return Response(serializer.data)

        # Generate basic stats if no recent analytics
        return Response(
            {"message": "No recent analytics available. Generate a new report."}
        )
