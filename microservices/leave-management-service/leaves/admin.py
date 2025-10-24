from django.contrib import admin
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import (LeaveApproval, LeaveBalance, LeavePolicy, LeaveRequest,
                     LeaveType)


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "category",
        "applicable_to",
        "max_days_per_request",
        "max_days_per_year",
        "requires_approval",
        "is_active",
    ]
    list_filter = ["category", "applicable_to", "requires_approval", "is_active"]
    search_fields = ["name", "description"]
    ordering = ["name"]

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("name", "category", "description", "applicable_to")},
        ),
        (
            "Limits & Rules",
            {
                "fields": (
                    "max_days_per_request",
                    "max_days_per_year",
                    "advance_notice_days",
                )
            },
        ),
        ("Approval Settings", {"fields": ("requires_approval", "is_active")}),
    )


class LeaveApprovalInline(admin.TabularInline):
    model = LeaveApproval
    extra = 0
    readonly_fields = ["action_date"]
    fields = ["approver_name", "action", "comments", "action_date"]


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = [
        "user_name",
        "leave_type",
        "start_date",
        "end_date",
        "total_days",
        "status",
        "priority",
        "created_at",
    ]
    list_filter = ["status", "priority", "user_type", "leave_type", "created_at"]
    search_fields = ["user_name", "user_email", "reason"]
    ordering = ["-created_at"]
    readonly_fields = ["total_days", "created_at", "updated_at", "submitted_at"]

    fieldsets = (
        (
            "User Information",
            {"fields": ("user_id", "user_type", "user_name", "user_email")},
        ),
        (
            "Leave Details",
            {
                "fields": (
                    "leave_type",
                    "start_date",
                    "end_date",
                    "total_days",
                    "reason",
                    "emergency_contact",
                    "attachment",
                )
            },
        ),
        ("Status & Priority", {"fields": ("status", "priority", "rejection_reason")}),
        (
            "Approval Information",
            {"fields": ("approver_id", "approver_name", "approved_at")},
        ),
        (
            "Academic Context",
            {"fields": ("academic_year", "semester"), "classes": ("collapse",)},
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at", "submitted_at"),
                "classes": ("collapse",),
            },
        ),
    )

    inlines = [LeaveApprovalInline]

    actions = ["approve_selected", "reject_selected", "mark_as_pending"]

    def approve_selected(self, request, queryset):
        updated = queryset.filter(status="PENDING").update(
            status="APPROVED",
            approver_id="admin",
            approver_name=request.user.get_full_name() or request.user.username,
            approved_at=timezone.now(),
        )
        self.message_user(request, f"{updated} leave requests approved.")

    approve_selected.short_description = "Approve selected pending requests"

    def reject_selected(self, request, queryset):
        updated = queryset.filter(status="PENDING").update(
            status="REJECTED",
            approver_id="admin",
            approver_name=request.user.get_full_name() or request.user.username,
            rejection_reason="Rejected by admin",
        )
        self.message_user(request, f"{updated} leave requests rejected.")

    reject_selected.short_description = "Reject selected pending requests"

    def mark_as_pending(self, request, queryset):
        updated = queryset.exclude(status="PENDING").update(status="PENDING")
        self.message_user(request, f"{updated} leave requests marked as pending.")

    mark_as_pending.short_description = "Mark as pending"


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = [
        "user_id",
        "leave_type",
        "year",
        "total_allocated",
        "used_days",
        "pending_days",
        "available_days",
    ]
    list_filter = ["user_type", "leave_type", "year"]
    search_fields = ["user_id"]
    ordering = ["-year", "user_id"]
    readonly_fields = ["available_days", "utilization_percentage"]

    fieldsets = (
        (
            "User & Leave Type",
            {"fields": ("user_id", "user_type", "leave_type", "year", "academic_year")},
        ),
        (
            "Balance Information",
            {
                "fields": (
                    "total_allocated",
                    "used_days",
                    "pending_days",
                    "available_days",
                    "utilization_percentage",
                )
            },
        ),
    )


@admin.register(LeaveApproval)
class LeaveApprovalAdmin(admin.ModelAdmin):
    list_display = [
        "leave_request_summary",
        "approver_name",
        "action",
        "action_date",
        "previous_status",
        "new_status",
    ]
    list_filter = ["action", "approver_type", "action_date"]
    search_fields = ["approver_name", "comments"]
    ordering = ["-action_date"]
    readonly_fields = ["action_date"]

    def leave_request_summary(self, obj):
        return f"{obj.leave_request.user_name} - {obj.leave_request.leave_type.name}"

    leave_request_summary.short_description = "Leave Request"

    fieldsets = (
        ("Leave Request", {"fields": ("leave_request",)}),
        (
            "Approver Information",
            {"fields": ("approver_id", "approver_name", "approver_type")},
        ),
        ("Action Details", {"fields": ("action", "comments", "action_date")}),
        ("Status Change", {"fields": ("previous_status", "new_status")}),
    )


@admin.register(LeavePolicy)
class LeavePolicyAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "policy_type",
        "user_type",
        "leave_type",
        "is_active",
        "effective_from",
        "effective_to",
    ]
    list_filter = ["policy_type", "user_type", "is_active", "effective_from"]
    search_fields = ["name", "description"]
    ordering = ["name"]

    fieldsets = (
        ("Basic Information", {"fields": ("name", "policy_type", "description")}),
        ("Applicability", {"fields": ("leave_type", "user_type")}),
        ("Policy Rules", {"fields": ("rules",)}),
        (
            "Effective Period",
            {"fields": ("is_active", "effective_from", "effective_to")},
        ),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Add help text for JSON rules field
        form.base_fields[
            "rules"
        ].help_text = """
        Enter policy rules in JSON format. Examples:
        - Annual allocation: {"days": 30, "carryover": 5}
        - Blackout dates: {"dates": ["2024-12-25", "2024-01-01"]}
        - Approval hierarchy: {"levels": ["supervisor", "hr", "admin"]}
        """
        return form


# Custom admin site configuration
admin.site.site_header = "Leave Management Administration"
admin.site.site_title = "Leave Management Admin"
admin.site.index_title = "Welcome to Leave Management Administration"
