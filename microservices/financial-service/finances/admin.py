from django.contrib import admin
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import (FeeStructure, FinancialReport, Fine, FinePayment, Invoice,
                     Payment, StudentFee, Transaction)


@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "fee_type",
        "course_name",
        "academic_year",
        "semester",
        "amount",
        "currency",
        "due_date",
        "is_active",
        "created_at",
    ]
    list_filter = [
        "fee_type",
        "academic_year",
        "semester",
        "is_active",
        "mandatory",
        "frequency",
        "late_fee_applicable",
    ]
    search_fields = ["name", "description", "course_name", "course_id"]
    readonly_fields = ["id", "created_at", "updated_at"]
    fieldsets = (
        ("Basic Information", {"fields": ("name", "description", "fee_type")}),
        (
            "Academic Context",
            {"fields": ("course_id", "course_name", "academic_year", "semester")},
        ),
        ("Fee Details", {"fields": ("amount", "currency", "frequency", "due_date")}),
        (
            "Late Fee Settings",
            {
                "fields": (
                    "late_fee_applicable",
                    "late_fee_amount",
                    "late_fee_percentage",
                )
            },
        ),
        ("Applicability", {"fields": ("applicable_to", "mandatory")}),
        (
            "Payment Settings",
            {
                "fields": (
                    "allow_partial_payment",
                    "installment_allowed",
                    "max_installments",
                )
            },
        ),
        ("Status", {"fields": ("is_active",)}),
        (
            "Metadata",
            {
                "fields": ("id", "created_by", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related()

    actions = ["activate_structures", "deactivate_structures", "duplicate_for_new_year"]

    def activate_structures(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} fee structures activated.")

    activate_structures.short_description = "Activate selected fee structures"

    def deactivate_structures(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} fee structures deactivated.")

    deactivate_structures.short_description = "Deactivate selected fee structures"

    def duplicate_for_new_year(self, request, queryset):
        # This would open a form to specify new academic year
        self.message_user(
            request,
            "Use the API endpoint for bulk duplication with academic year specification.",
        )

    duplicate_for_new_year.short_description = "Duplicate for new academic year"


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ["id", "payment_date", "processed_at", "gateway_transaction_id"]
    fields = [
        "amount",
        "payment_method",
        "status",
        "payment_date",
        "receipt_number",
        "notes",
    ]

    def has_add_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StudentFee)
class StudentFeeAdmin(admin.ModelAdmin):
    list_display = [
        "student_name",
        "fee_structure_name",
        "fee_type",
        "final_amount",
        "paid_amount",
        "balance_amount",
        "status",
        "due_date",
        "is_overdue",
    ]
    list_filter = [
        "status",
        "is_overdue",
        "fee_structure__fee_type",
        "fee_structure__academic_year",
        "due_date",
    ]
    search_fields = [
        "student_name",
        "student_email",
        "student_id",
        "fee_structure__name",
    ]
    readonly_fields = [
        "id",
        "balance_amount",
        "payment_count",
        "last_payment_date",
        "created_at",
        "updated_at",
    ]
    inlines = [PaymentInline]

    fieldsets = (
        (
            "Student Information",
            {"fields": ("student_id", "student_name", "student_email")},
        ),
        ("Fee Structure", {"fields": ("fee_structure",)}),
        (
            "Amount Details",
            {
                "fields": (
                    "original_amount",
                    "discount_amount",
                    "late_fee_amount",
                    "final_amount",
                    "paid_amount",
                    "balance_amount",
                )
            },
        ),
        ("Status & Timing", {"fields": ("status", "due_date", "is_overdue")}),
        (
            "Payment Tracking",
            {
                "fields": ("payment_count", "last_payment_date"),
                "classes": ("collapse",),
            },
        ),
        (
            "Discounts & Waivers",
            {
                "fields": (
                    "discount_reason",
                    "waiver_reason",
                    "waived_by",
                    "waived_at",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Metadata",
            {"fields": ("id", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def fee_structure_name(self, obj):
        return obj.fee_structure.name

    fee_structure_name.short_description = "Fee Structure"

    def fee_type(self, obj):
        return obj.fee_structure.get_fee_type_display()

    fee_type.short_description = "Fee Type"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("fee_structure")

    actions = ["mark_as_paid", "apply_discount", "waive_fees", "send_reminders"]

    def mark_as_paid(self, request, queryset):
        updated = 0
        for student_fee in queryset:
            if student_fee.status != "PAID":
                student_fee.paid_amount = student_fee.final_amount
                student_fee.status = "PAID"
                student_fee.last_payment_date = timezone.now()
                student_fee.save()
                updated += 1
        self.message_user(request, f"{updated} student fees marked as paid.")

    mark_as_paid.short_description = "Mark selected fees as paid"

    def apply_discount(self, request, queryset):
        self.message_user(
            request, "Use individual fee edit or API for discount application."
        )

    apply_discount.short_description = "Apply discount to selected fees"

    def waive_fees(self, request, queryset):
        updated = queryset.update(
            status="WAIVED",
            waiver_reason="Admin waiver",
            waived_by=request.user.username,
            waived_at=timezone.now(),
        )
        self.message_user(request, f"{updated} fees waived.")

    waive_fees.short_description = "Waive selected fees"

    def send_reminders(self, request, queryset):
        from .tasks import send_payment_reminder

        count = 0
        for student_fee in queryset.filter(
            status__in=["PENDING", "PARTIALLY_PAID", "OVERDUE"]
        ):
            send_payment_reminder.delay(student_fee.id)
            count += 1
        self.message_user(request, f"Payment reminders sent for {count} fees.")

    send_reminders.short_description = "Send payment reminders"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        "receipt_number",
        "student_name",
        "amount",
        "currency",
        "payment_method",
        "payment_gateway",
        "status",
        "payment_date",
    ]
    list_filter = [
        "status",
        "payment_method",
        "payment_gateway",
        "payment_date",
        "verification_status",
    ]
    search_fields = [
        "receipt_number",
        "reference_number",
        "gateway_transaction_id",
        "student_fee__student_name",
        "student_fee__student_email",
    ]
    readonly_fields = ["id", "payment_date", "processed_at", "gateway_response"]

    fieldsets = (
        (
            "Payment Details",
            {
                "fields": (
                    "student_fee",
                    "amount",
                    "currency",
                    "payment_method",
                    "payment_gateway",
                )
            },
        ),
        (
            "Gateway Information",
            {
                "fields": (
                    "gateway_transaction_id",
                    "gateway_payment_id",
                    "gateway_order_id",
                    "gateway_response",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Status & Timing",
            {
                "fields": (
                    "status",
                    "payment_date",
                    "processed_at",
                    "verification_status",
                )
            },
        ),
        (
            "Additional Details",
            {"fields": ("reference_number", "receipt_number", "notes")},
        ),
        ("Processing Info", {"fields": ("processed_by",)}),
        (
            "Refund Details",
            {
                "fields": ("refund_amount", "refund_reason", "refunded_at"),
                "classes": ("collapse",),
            },
        ),
        ("Metadata", {"fields": ("id",), "classes": ("collapse",)}),
    )

    def student_name(self, obj):
        return obj.student_fee.student_name

    student_name.short_description = "Student"

    def get_queryset(self, request):
        return (
            super().get_queryset(request).select_related("student_fee__fee_structure")
        )

    actions = ["verify_payments", "mark_as_failed", "process_refunds"]

    def verify_payments(self, request, queryset):
        updated = queryset.filter(status="PENDING").update(
            status="SUCCESS",
            processed_at=timezone.now(),
            processed_by=request.user.username,
        )
        self.message_user(request, f"{updated} payments verified.")

    verify_payments.short_description = "Verify selected payments"

    def mark_as_failed(self, request, queryset):
        updated = queryset.filter(status="PENDING").update(status="FAILED")
        self.message_user(request, f"{updated} payments marked as failed.")

    mark_as_failed.short_description = "Mark selected payments as failed"

    def process_refunds(self, request, queryset):
        self.message_user(request, "Use individual payment edit for refund processing.")

    process_refunds.short_description = "Process refunds for selected payments"


class FinePaymentInline(admin.TabularInline):
    model = FinePayment
    extra = 0
    readonly_fields = ["id", "payment_date"]
    fields = [
        "amount",
        "payment_method",
        "status",
        "payment_date",
        "receipt_number",
        "notes",
    ]


@admin.register(Fine)
class FineAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "student_name",
        "fine_type",
        "amount",
        "balance_amount",
        "status",
        "due_date",
        "issued_date",
    ]
    list_filter = ["fine_type", "status", "issued_date", "due_date", "department"]
    search_fields = [
        "title",
        "description",
        "student_name",
        "student_email",
        "student_id",
    ]
    readonly_fields = ["id", "issued_date", "paid_date", "balance_amount"]
    inlines = [FinePaymentInline]

    fieldsets = (
        (
            "Student Information",
            {"fields": ("student_id", "student_name", "student_email")},
        ),
        (
            "Fine Details",
            {"fields": ("fine_type", "title", "description", "amount", "currency")},
        ),
        (
            "Status & Timing",
            {"fields": ("status", "issued_date", "due_date", "paid_date")},
        ),
        ("Issuing Authority", {"fields": ("issued_by", "issuer_name", "department")}),
        (
            "Payment Tracking",
            {"fields": ("paid_amount", "balance_amount"), "classes": ("collapse",)},
        ),
        (
            "Waiver Details",
            {
                "fields": ("waiver_reason", "waived_by", "waived_at"),
                "classes": ("collapse",),
            },
        ),
        (
            "Additional Details",
            {"fields": ("reference_id", "attachments"), "classes": ("collapse",)},
        ),
        ("Metadata", {"fields": ("id",), "classes": ("collapse",)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request)

    actions = ["waive_fines", "mark_as_paid", "send_fine_reminders"]

    def waive_fines(self, request, queryset):
        updated = queryset.filter(status="ACTIVE").update(
            status="WAIVED",
            waiver_reason="Admin waiver",
            waived_by=request.user.username,
            waived_at=timezone.now(),
        )
        self.message_user(request, f"{updated} fines waived.")

    waive_fines.short_description = "Waive selected fines"

    def mark_as_paid(self, request, queryset):
        updated = 0
        for fine in queryset.filter(status="ACTIVE"):
            fine.paid_amount = fine.amount
            fine.status = "PAID"
            fine.paid_date = timezone.now()
            fine.save()
            updated += 1
        self.message_user(request, f"{updated} fines marked as paid.")

    mark_as_paid.short_description = "Mark selected fines as paid"

    def send_fine_reminders(self, request, queryset):
        # This would trigger fine reminder notifications
        count = queryset.filter(status="ACTIVE").count()
        self.message_user(request, f"Fine reminders would be sent for {count} fines.")

    send_fine_reminders.short_description = "Send fine reminders"


@admin.register(FinePayment)
class FinePaymentAdmin(admin.ModelAdmin):
    list_display = [
        "receipt_number",
        "fine_title",
        "student_name",
        "amount",
        "payment_method",
        "status",
        "payment_date",
    ]
    list_filter = ["status", "payment_method", "payment_date"]
    search_fields = [
        "receipt_number",
        "reference_number",
        "fine__title",
        "fine__student_name",
    ]
    readonly_fields = ["id", "payment_date"]

    fieldsets = (
        ("Payment Details", {"fields": ("fine", "amount", "payment_method", "status")}),
        (
            "Payment Tracking",
            {"fields": ("payment_date", "reference_number", "receipt_number")},
        ),
        ("Processing Info", {"fields": ("processed_by", "notes")}),
        ("Metadata", {"fields": ("id",), "classes": ("collapse",)}),
    )

    def fine_title(self, obj):
        return obj.fine.title

    fine_title.short_description = "Fine"

    def student_name(self, obj):
        return obj.fine.student_name

    student_name.short_description = "Student"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("fine")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        "transaction_type",
        "student_name",
        "amount",
        "currency",
        "status",
        "transaction_date",
        "reference_type",
    ]
    list_filter = ["transaction_type", "status", "transaction_date", "reference_type"]
    search_fields = [
        "description",
        "student_name",
        "student_id",
        "reference_id",
        "payment_id",
    ]
    readonly_fields = ["id", "transaction_date", "processed_at"]

    fieldsets = (
        (
            "Transaction Details",
            {"fields": ("transaction_type", "amount", "currency", "description")},
        ),
        ("Parties Involved", {"fields": ("student_id", "student_name")}),
        ("References", {"fields": ("reference_type", "reference_id", "payment_id")}),
        ("Status & Timing", {"fields": ("status", "transaction_date", "processed_at")}),
        ("Processing Info", {"fields": ("processed_by", "notes")}),
        (
            "Accounting",
            {"fields": ("debit_account", "credit_account"), "classes": ("collapse",)},
        ),
        ("Additional Data", {"fields": ("metadata",), "classes": ("collapse",)}),
        ("Metadata", {"fields": ("id",), "classes": ("collapse",)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request)

    def has_add_permission(self, request):
        return False  # Transactions are created automatically

    def has_delete_permission(self, request, obj=None):
        return False  # Transactions should not be deleted


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        "invoice_number",
        "student_name",
        "invoice_date",
        "due_date",
        "total_amount",
        "paid_amount",
        "balance_amount",
        "status",
    ]
    list_filter = ["status", "invoice_date", "due_date"]
    search_fields = ["invoice_number", "student_name", "student_email", "student_id"]
    readonly_fields = [
        "id",
        "invoice_number",
        "invoice_date",
        "balance_amount",
        "created_at",
        "updated_at",
    ]

    fieldsets = (
        (
            "Invoice Details",
            {"fields": ("invoice_number", "invoice_date", "due_date", "status")},
        ),
        (
            "Student Information",
            {
                "fields": (
                    "student_id",
                    "student_name",
                    "student_email",
                    "billing_address",
                )
            },
        ),
        (
            "Amounts",
            {
                "fields": (
                    "subtotal",
                    "tax_amount",
                    "discount_amount",
                    "total_amount",
                    "paid_amount",
                    "balance_amount",
                )
            },
        ),
        ("Line Items", {"fields": ("line_items",), "classes": ("collapse",)}),
        (
            "Additional Details",
            {"fields": ("notes", "terms_and_conditions"), "classes": ("collapse",)},
        ),
        (
            "Metadata",
            {
                "fields": ("id", "created_by", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request)

    actions = ["send_invoices", "mark_as_sent", "cancel_invoices"]

    def send_invoices(self, request, queryset):
        from .tasks import generate_invoice_task

        count = 0
        for invoice in queryset:
            generate_invoice_task.delay(invoice.id, send_email=True)
            count += 1
        self.message_user(request, f"Sending {count} invoices.")

    send_invoices.short_description = "Send selected invoices"

    def mark_as_sent(self, request, queryset):
        updated = queryset.filter(status="DRAFT").update(status="SENT")
        self.message_user(request, f"{updated} invoices marked as sent.")

    mark_as_sent.short_description = "Mark selected invoices as sent"

    def cancel_invoices(self, request, queryset):
        updated = queryset.exclude(status="PAID").update(status="CANCELLED")
        self.message_user(request, f"{updated} invoices cancelled.")

    cancel_invoices.short_description = "Cancel selected invoices"


@admin.register(FinancialReport)
class FinancialReportAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "report_type",
        "start_date",
        "end_date",
        "total_collections",
        "total_outstanding",
        "generated_at",
    ]
    list_filter = ["report_type", "generated_at", "start_date"]
    search_fields = ["title", "generated_by"]
    readonly_fields = ["id", "generated_at", "report_data", "summary"]

    fieldsets = (
        (
            "Report Details",
            {"fields": ("report_type", "title", "start_date", "end_date")},
        ),
        (
            "Financial Summary",
            {
                "fields": (
                    "total_collections",
                    "total_outstanding",
                    "total_fines",
                    "total_refunds",
                )
            },
        ),
        (
            "Detailed Data",
            {"fields": ("report_data", "summary"), "classes": ("collapse",)},
        ),
        (
            "Metadata",
            {
                "fields": ("id", "generated_by", "generated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request)

    actions = ["regenerate_reports"]

    def regenerate_reports(self, request, queryset):
        from .tasks import generate_financial_reports

        generate_financial_reports.delay()
        self.message_user(request, "Financial reports regeneration initiated.")

    regenerate_reports.short_description = "Regenerate financial reports"


# Customize admin site
admin.site.site_header = "Financial Service Administration"
admin.site.site_title = "Financial Service Admin"
admin.site.index_title = "Welcome to Financial Service Administration"
