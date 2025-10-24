from django.contrib import admin
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import (Feedback, FeedbackAnalytics, FeedbackCategory,
                     FeedbackResponse, FeedbackSurvey, FeedbackTemplate)


@admin.register(FeedbackCategory)
class FeedbackCategoryAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "category_type",
        "target_audience",
        "is_active",
        "requires_moderation",
        "allow_anonymous",
        "display_order",
    ]
    list_filter = [
        "category_type",
        "target_audience",
        "is_active",
        "requires_moderation",
    ]
    search_fields = ["name", "description"]
    ordering = ["display_order", "name"]

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("name", "category_type", "description", "target_audience")},
        ),
        (
            "Settings",
            {
                "fields": (
                    "is_active",
                    "requires_moderation",
                    "allow_anonymous",
                    "display_order",
                )
            },
        ),
    )


class FeedbackResponseInline(admin.TabularInline):
    model = FeedbackResponse
    extra = 0
    readonly_fields = ["created_at"]
    fields = [
        "responder_name",
        "response_type",
        "message",
        "is_public",
        "is_final",
        "created_at",
    ]


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "user_display",
        "category",
        "rating",
        "status",
        "priority",
        "sentiment",
        "created_at",
    ]
    list_filter = [
        "status",
        "priority",
        "rating",
        "category",
        "user_type",
        "sentiment",
        "is_public",
        "is_featured",
        "created_at",
    ]
    search_fields = ["title", "description", "user_name", "user_email", "target_name"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at", "updated_at", "submitted_at", "response_count"]

    fieldsets = (
        (
            "User Information",
            {
                "fields": (
                    "user_id",
                    "user_type",
                    "user_name",
                    "user_email",
                    "is_anonymous",
                )
            },
        ),
        (
            "Feedback Details",
            {
                "fields": (
                    "category",
                    "title",
                    "description",
                    "rating",
                    "attachments",
                    "tags",
                )
            },
        ),
        ("Target Information", {"fields": ("target_type", "target_id", "target_name")}),
        (
            "Status & Processing",
            {"fields": ("status", "priority", "sentiment", "is_public", "is_featured")},
        ),
        (
            "Moderation",
            {
                "fields": (
                    "moderator_id",
                    "moderator_name",
                    "moderated_at",
                    "moderation_notes",
                )
            },
        ),
        (
            "Academic Context",
            {"fields": ("academic_year", "semester"), "classes": ("collapse",)},
        ),
        (
            "Metadata",
            {
                "fields": (
                    "metadata",
                    "created_at",
                    "updated_at",
                    "submitted_at",
                    "response_count",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    inlines = [FeedbackResponseInline]

    actions = [
        "approve_selected",
        "reject_selected",
        "feature_selected",
        "unfeature_selected",
    ]

    def user_display(self, obj):
        if obj.is_anonymous:
            return "Anonymous"
        return obj.user_name or f"User {obj.user_id}"

    user_display.short_description = "User"

    def response_count(self, obj):
        return obj.responses.count()

    response_count.short_description = "Responses"

    def approve_selected(self, request, queryset):
        updated = queryset.filter(status__in=["SUBMITTED", "UNDER_REVIEW"]).update(
            status="APPROVED",
            moderator_id="admin",
            moderator_name=request.user.get_full_name() or request.user.username,
            moderated_at=timezone.now(),
        )
        self.message_user(request, f"{updated} feedback entries approved.")

    approve_selected.short_description = "Approve selected feedback"

    def reject_selected(self, request, queryset):
        updated = queryset.filter(status__in=["SUBMITTED", "UNDER_REVIEW"]).update(
            status="REJECTED",
            moderator_id="admin",
            moderator_name=request.user.get_full_name() or request.user.username,
            moderated_at=timezone.now(),
        )
        self.message_user(request, f"{updated} feedback entries rejected.")

    reject_selected.short_description = "Reject selected feedback"

    def feature_selected(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f"{updated} feedback entries featured.")

    feature_selected.short_description = "Feature selected feedback"

    def unfeature_selected(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f"{updated} feedback entries unfeatured.")

    unfeature_selected.short_description = "Unfeature selected feedback"


@admin.register(FeedbackResponse)
class FeedbackResponseAdmin(admin.ModelAdmin):
    list_display = [
        "feedback_title",
        "responder_name",
        "response_type",
        "is_public",
        "is_final",
        "created_at",
    ]
    list_filter = [
        "response_type",
        "responder_type",
        "is_public",
        "is_final",
        "created_at",
    ]
    search_fields = ["message", "responder_name", "feedback__title"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at", "updated_at"]

    def feedback_title(self, obj):
        return obj.feedback.title

    feedback_title.short_description = "Feedback"

    fieldsets = (
        (
            "Response Details",
            {"fields": ("feedback", "response_type", "message", "attachments")},
        ),
        (
            "Responder Information",
            {
                "fields": (
                    "responder_id",
                    "responder_name",
                    "responder_type",
                    "responder_designation",
                )
            },
        ),
        ("Settings", {"fields": ("is_public", "is_final")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(FeedbackTemplate)
class FeedbackTemplateAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "template_type",
        "target_audience",
        "is_active",
        "is_mandatory",
        "start_date",
        "end_date",
    ]
    list_filter = ["template_type", "target_audience", "is_active", "is_mandatory"]
    search_fields = ["name", "description"]
    ordering = ["name"]
    filter_horizontal = ["categories"]

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("name", "template_type", "description", "target_audience")},
        ),
        ("Template Structure", {"fields": ("questions", "categories")}),
        ("Settings", {"fields": ("is_active", "is_mandatory", "allow_anonymous")}),
        ("Schedule", {"fields": ("start_date", "end_date")}),
        (
            "Metadata",
            {
                "fields": ("created_by", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    readonly_fields = ["created_at", "updated_at"]


@admin.register(FeedbackSurvey)
class FeedbackSurveyAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "template_name",
        "target_name",
        "status",
        "total_participants",
        "responses_count",
        "completion_rate",
        "start_date",
        "end_date",
    ]
    list_filter = [
        "status",
        "target_type",
        "target_audience",
        "is_anonymous",
        "created_at",
    ]
    search_fields = ["title", "description", "target_name"]
    ordering = ["-created_at"]
    readonly_fields = [
        "total_participants",
        "responses_count",
        "completion_rate",
        "created_at",
        "updated_at",
        "is_active",
        "days_remaining",
    ]

    def template_name(self, obj):
        return obj.template.name

    template_name.short_description = "Template"

    fieldsets = (
        ("Basic Information", {"fields": ("title", "description", "template")}),
        (
            "Target Information",
            {"fields": ("target_type", "target_id", "target_name", "target_audience")},
        ),
        ("Participants", {"fields": ("participant_ids", "total_participants")}),
        (
            "Settings",
            {
                "fields": (
                    "status",
                    "is_anonymous",
                    "allow_multiple_responses",
                    "reminder_frequency",
                )
            },
        ),
        (
            "Schedule",
            {"fields": ("start_date", "end_date", "is_active", "days_remaining")},
        ),
        ("Statistics", {"fields": ("responses_count", "completion_rate")}),
        (
            "Academic Context",
            {"fields": ("academic_year", "semester"), "classes": ("collapse",)},
        ),
        (
            "Metadata",
            {
                "fields": ("created_by", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(FeedbackAnalytics)
class FeedbackAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "report_type",
        "start_date",
        "end_date",
        "total_feedback",
        "average_rating",
        "generated_by",
        "generated_at",
    ]
    list_filter = ["report_type", "generated_by", "generated_at"]
    search_fields = ["title"]
    ordering = ["-generated_at"]
    readonly_fields = ["generated_at"]

    fieldsets = (
        (
            "Report Information",
            {"fields": ("report_type", "title", "start_date", "end_date")},
        ),
        ("Filters", {"fields": ("categories", "target_types")}),
        (
            "Key Metrics",
            {"fields": ("total_feedback", "average_rating", "response_rate")},
        ),
        (
            "Distributions",
            {
                "fields": (
                    "sentiment_distribution",
                    "category_breakdown",
                    "rating_distribution",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Analysis",
            {
                "fields": ("insights", "trends", "recommendations"),
                "classes": ("collapse",),
            },
        ),
        (
            "Metadata",
            {"fields": ("generated_by", "generated_at"), "classes": ("collapse",)},
        ),
    )


# Custom admin site configuration
admin.site.site_header = "Feedback Management Administration"
admin.site.site_title = "Feedback Management Admin"
admin.site.index_title = "Welcome to Feedback Management Administration"
