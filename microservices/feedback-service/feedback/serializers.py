from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from .models import (Feedback, FeedbackAnalytics, FeedbackCategory,
                     FeedbackResponse, FeedbackSurvey, FeedbackTemplate)


class FeedbackCategorySerializer(serializers.ModelSerializer):
    """Serializer for FeedbackCategory model"""

    feedback_count = serializers.SerializerMethodField()
    category_type_display = serializers.CharField(
        source="get_category_type_display", read_only=True
    )
    target_audience_display = serializers.CharField(
        source="get_target_audience_display", read_only=True
    )

    class Meta:
        model = FeedbackCategory
        fields = [
            "id",
            "name",
            "category_type",
            "category_type_display",
            "description",
            "target_audience",
            "target_audience_display",
            "is_active",
            "requires_moderation",
            "allow_anonymous",
            "display_order",
            "feedback_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_feedback_count(self, obj):
        return obj.feedbacks.count()


class FeedbackResponseSerializer(serializers.ModelSerializer):
    """Serializer for FeedbackResponse model"""

    response_type_display = serializers.CharField(
        source="get_response_type_display", read_only=True
    )

    class Meta:
        model = FeedbackResponse
        fields = [
            "id",
            "feedback",
            "responder_id",
            "responder_name",
            "responder_type",
            "responder_designation",
            "response_type",
            "response_type_display",
            "message",
            "attachments",
            "is_public",
            "is_final",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class FeedbackSerializer(serializers.ModelSerializer):
    """Serializer for Feedback model"""

    category_name = serializers.CharField(source="category.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    priority_display = serializers.CharField(
        source="get_priority_display", read_only=True
    )
    sentiment_display = serializers.CharField(
        source="get_sentiment_display", read_only=True
    )
    is_recent = serializers.BooleanField(read_only=True)
    response_count = serializers.IntegerField(read_only=True)
    responses = FeedbackResponseSerializer(many=True, read_only=True)

    class Meta:
        model = Feedback
        fields = [
            "id",
            "user_id",
            "user_type",
            "user_name",
            "user_email",
            "is_anonymous",
            "category",
            "category_name",
            "title",
            "description",
            "rating",
            "target_type",
            "target_id",
            "target_name",
            "status",
            "status_display",
            "priority",
            "priority_display",
            "sentiment",
            "sentiment_display",
            "moderator_id",
            "moderator_name",
            "moderated_at",
            "moderation_notes",
            "attachments",
            "tags",
            "metadata",
            "academic_year",
            "semester",
            "is_public",
            "is_featured",
            "is_recent",
            "response_count",
            "responses",
            "created_at",
            "updated_at",
            "submitted_at",
        ]
        read_only_fields = [
            "id",
            "moderator_id",
            "moderator_name",
            "moderated_at",
            "created_at",
            "updated_at",
            "submitted_at",
        ]

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value

    def validate(self, data):
        category = data.get("category")
        is_anonymous = data.get("is_anonymous", False)
        user_id = data.get("user_id")

        # Validate anonymous feedback
        if is_anonymous and not category.allow_anonymous:
            raise serializers.ValidationError(
                "Anonymous feedback is not allowed for this category"
            )

        # Validate user information for non-anonymous feedback
        if not is_anonymous and not user_id:
            raise serializers.ValidationError(
                "User ID is required for non-anonymous feedback"
            )

        return data


class FeedbackCreateSerializer(FeedbackSerializer):
    """Serializer for creating feedback"""

    class Meta(FeedbackSerializer.Meta):
        fields = [
            "user_id",
            "user_type",
            "user_name",
            "user_email",
            "is_anonymous",
            "category",
            "title",
            "description",
            "rating",
            "target_type",
            "target_id",
            "target_name",
            "priority",
            "attachments",
            "tags",
            "metadata",
            "academic_year",
            "semester",
        ]


class FeedbackUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating feedback status"""

    class Meta:
        model = Feedback
        fields = [
            "status",
            "priority",
            "sentiment",
            "moderator_id",
            "moderator_name",
            "moderation_notes",
            "is_public",
            "is_featured",
        ]

    def validate_status(self, value):
        instance = self.instance
        if instance and instance.status == "CLOSED" and value != "CLOSED":
            raise serializers.ValidationError("Cannot modify closed feedback")
        return value


class FeedbackTemplateSerializer(serializers.ModelSerializer):
    """Serializer for FeedbackTemplate model"""

    template_type_display = serializers.CharField(
        source="get_template_type_display", read_only=True
    )
    target_audience_display = serializers.CharField(
        source="get_target_audience_display", read_only=True
    )
    category_names = serializers.SerializerMethodField()

    class Meta:
        model = FeedbackTemplate
        fields = [
            "id",
            "name",
            "template_type",
            "template_type_display",
            "description",
            "questions",
            "target_audience",
            "target_audience_display",
            "categories",
            "category_names",
            "is_active",
            "is_mandatory",
            "allow_anonymous",
            "start_date",
            "end_date",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_category_names(self, obj):
        return [category.name for category in obj.categories.all()]

    def validate(self, data):
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        if start_date and end_date and start_date >= end_date:
            raise serializers.ValidationError("Start date must be before end date")

        return data


class FeedbackSurveySerializer(serializers.ModelSerializer):
    """Serializer for FeedbackSurvey model"""

    template_name = serializers.CharField(source="template.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    target_audience_display = serializers.CharField(
        source="get_target_audience_display", read_only=True
    )
    is_active = serializers.BooleanField(read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)

    class Meta:
        model = FeedbackSurvey
        fields = [
            "id",
            "title",
            "description",
            "template",
            "template_name",
            "target_type",
            "target_id",
            "target_name",
            "target_audience",
            "target_audience_display",
            "participant_ids",
            "status",
            "status_display",
            "is_anonymous",
            "allow_multiple_responses",
            "start_date",
            "end_date",
            "reminder_frequency",
            "academic_year",
            "semester",
            "total_participants",
            "responses_count",
            "completion_rate",
            "is_active",
            "days_remaining",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "total_participants",
            "responses_count",
            "completion_rate",
            "created_at",
            "updated_at",
        ]

    def validate(self, data):
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        if start_date and end_date:
            if start_date >= end_date:
                raise serializers.ValidationError("Start date must be before end date")

            if start_date < timezone.now():
                raise serializers.ValidationError("Start date cannot be in the past")

        return data


class FeedbackAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for FeedbackAnalytics model"""

    report_type_display = serializers.CharField(
        source="get_report_type_display", read_only=True
    )

    class Meta:
        model = FeedbackAnalytics
        fields = [
            "id",
            "report_type",
            "report_type_display",
            "title",
            "start_date",
            "end_date",
            "categories",
            "target_types",
            "total_feedback",
            "average_rating",
            "sentiment_distribution",
            "category_breakdown",
            "rating_distribution",
            "response_rate",
            "insights",
            "trends",
            "recommendations",
            "generated_by",
            "generated_at",
        ]
        read_only_fields = ["id", "generated_at"]


class BulkFeedbackSerializer(serializers.Serializer):
    """Serializer for bulk feedback creation"""

    category = serializers.PrimaryKeyRelatedField(
        queryset=FeedbackCategory.objects.filter(is_active=True)
    )
    title = serializers.CharField(max_length=200)
    description = serializers.CharField()
    rating = serializers.IntegerField(min_value=1, max_value=5)
    target_type = serializers.CharField(max_length=50, required=False)
    target_id = serializers.CharField(max_length=100, required=False)
    target_name = serializers.CharField(max_length=200, required=False)
    user_ids = serializers.ListField(
        child=serializers.CharField(max_length=100), min_length=1, max_length=100
    )
    is_anonymous = serializers.BooleanField(default=False)
    priority = serializers.ChoiceField(
        choices=Feedback.PRIORITY_CHOICES, default="MEDIUM"
    )


class FeedbackStatsSerializer(serializers.Serializer):
    """Serializer for feedback statistics"""

    total_feedback = serializers.IntegerField()
    pending_moderation = serializers.IntegerField()
    approved_feedback = serializers.IntegerField()
    rejected_feedback = serializers.IntegerField()
    average_rating = serializers.FloatField()

    # By category
    by_category = serializers.DictField()

    # By rating
    by_rating = serializers.DictField()

    # By sentiment
    by_sentiment = serializers.DictField()

    # By time period
    by_month = serializers.DictField()

    # Response metrics
    response_rate = serializers.FloatField()
    avg_response_time = serializers.FloatField()


class UserFeedbackHistorySerializer(serializers.Serializer):
    """Serializer for user feedback history"""

    user_id = serializers.CharField()
    user_name = serializers.CharField()
    total_feedback_given = serializers.IntegerField()
    average_rating_given = serializers.FloatField()
    feedback_categories = serializers.DictField()

    # Recent feedback
    recent_feedback = FeedbackSerializer(many=True, read_only=True)

    # Participation stats
    surveys_participated = serializers.IntegerField()
    response_rate = serializers.FloatField()


class FeedbackModerationSerializer(serializers.Serializer):
    """Serializer for feedback moderation actions"""

    feedback_ids = serializers.ListField(
        child=serializers.UUIDField(), min_length=1, max_length=50
    )
    action = serializers.ChoiceField(
        choices=["approve", "reject", "feature", "unfeature"]
    )
    moderation_notes = serializers.CharField(required=False, allow_blank=True)
    moderator_id = serializers.CharField(max_length=100)
    moderator_name = serializers.CharField(max_length=200)
