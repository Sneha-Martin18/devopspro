import json
import uuid
from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class FeeStructure(models.Model):
    """Model for defining fee structures for different courses and categories"""

    FEE_TYPES = [
        ("TUITION", "Tuition Fee"),
        ("ADMISSION", "Admission Fee"),
        ("EXAMINATION", "Examination Fee"),
        ("LIBRARY", "Library Fee"),
        ("LABORATORY", "Laboratory Fee"),
        ("SPORTS", "Sports Fee"),
        ("DEVELOPMENT", "Development Fee"),
        ("HOSTEL", "Hostel Fee"),
        ("TRANSPORT", "Transport Fee"),
        ("MISCELLANEOUS", "Miscellaneous Fee"),
    ]

    FREQUENCY_CHOICES = [
        ("SEMESTER", "Per Semester"),
        ("ANNUAL", "Annual"),
        ("MONTHLY", "Monthly"),
        ("ONE_TIME", "One Time"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    fee_type = models.CharField(max_length=20, choices=FEE_TYPES)

    # Academic context
    course_id = models.CharField(max_length=100, blank=True)
    course_name = models.CharField(max_length=200, blank=True)
    academic_year = models.CharField(max_length=20)
    semester = models.CharField(max_length=20, blank=True)

    # Fee details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="INR")
    frequency = models.CharField(
        max_length=20, choices=FREQUENCY_CHOICES, default="SEMESTER"
    )

    # Applicability
    applicable_to = models.JSONField(
        default=list
    )  # List of user types or specific criteria
    mandatory = models.BooleanField(default=True)

    # Timing
    due_date = models.DateField(null=True, blank=True)
    late_fee_applicable = models.BooleanField(default=True)
    late_fee_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    late_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Settings
    is_active = models.BooleanField(default=True)
    allow_partial_payment = models.BooleanField(default=False)
    installment_allowed = models.BooleanField(default=False)
    max_installments = models.PositiveIntegerField(default=1)

    # Metadata
    created_by = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "fee_structures"
        indexes = [
            models.Index(fields=["course_id"]),
            models.Index(fields=["fee_type"]),
            models.Index(fields=["academic_year", "semester"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["due_date"]),
        ]
        ordering = ["fee_type", "name"]

    def __str__(self):
        return f"{self.name} - {self.course_name} ({self.academic_year})"


class StudentFee(models.Model):
    """Model for individual student fee assignments"""

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("PARTIALLY_PAID", "Partially Paid"),
        ("PAID", "Paid"),
        ("OVERDUE", "Overdue"),
        ("WAIVED", "Waived"),
        ("CANCELLED", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fee_structure = models.ForeignKey(
        FeeStructure, on_delete=models.CASCADE, related_name="student_fees"
    )

    # Student info
    student_id = models.CharField(max_length=100)
    student_name = models.CharField(max_length=200)
    student_email = models.EmailField()

    # Fee details
    original_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    late_fee_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Status and timing
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    due_date = models.DateField()
    is_overdue = models.BooleanField(default=False)

    # Payment tracking
    payment_count = models.PositiveIntegerField(default=0)
    last_payment_date = models.DateTimeField(null=True, blank=True)

    # Discounts and waivers
    discount_reason = models.TextField(blank=True)
    waiver_reason = models.TextField(blank=True)
    waived_by = models.CharField(max_length=100, blank=True)
    waived_at = models.DateTimeField(null=True, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "student_fees"
        indexes = [
            models.Index(fields=["student_id"]),
            models.Index(fields=["status"]),
            models.Index(fields=["due_date"]),
            models.Index(fields=["is_overdue"]),
            models.Index(fields=["fee_structure"]),
        ]
        unique_together = ["fee_structure", "student_id"]
        ordering = ["due_date", "-created_at"]

    def __str__(self):
        return f"{self.student_name} - {self.fee_structure.name}"

    def save(self, *args, **kwargs):
        # Calculate balance amount
        self.balance_amount = self.final_amount - self.paid_amount

        # Update status based on payment
        if self.paid_amount >= self.final_amount:
            self.status = "PAID"
        elif self.paid_amount > 0:
            self.status = "PARTIALLY_PAID"
        elif self.due_date < timezone.now().date():
            self.status = "OVERDUE"
            self.is_overdue = True

        super().save(*args, **kwargs)


class Payment(models.Model):
    """Model for recording payments"""

    PAYMENT_METHODS = [
        ("CASH", "Cash"),
        ("CARD", "Credit/Debit Card"),
        ("NET_BANKING", "Net Banking"),
        ("UPI", "UPI"),
        ("WALLET", "Digital Wallet"),
        ("CHEQUE", "Cheque"),
        ("DD", "Demand Draft"),
        ("BANK_TRANSFER", "Bank Transfer"),
    ]

    PAYMENT_STATUS = [
        ("PENDING", "Pending"),
        ("PROCESSING", "Processing"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
        ("CANCELLED", "Cancelled"),
        ("REFUNDED", "Refunded"),
    ]

    GATEWAY_CHOICES = [
        ("RAZORPAY", "Razorpay"),
        ("STRIPE", "Stripe"),
        ("PAYPAL", "PayPal"),
        ("PAYTM", "Paytm"),
        ("PHONEPE", "PhonePe"),
        ("GPAY", "Google Pay"),
        ("MANUAL", "Manual Entry"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student_fee = models.ForeignKey(
        StudentFee, on_delete=models.CASCADE, related_name="payments"
    )

    # Payment details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="INR")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    payment_gateway = models.CharField(
        max_length=20, choices=GATEWAY_CHOICES, default="MANUAL"
    )

    # Gateway details
    gateway_transaction_id = models.CharField(max_length=200, blank=True)
    gateway_payment_id = models.CharField(max_length=200, blank=True)
    gateway_order_id = models.CharField(max_length=200, blank=True)
    gateway_response = models.JSONField(default=dict, blank=True)

    # Status and timing
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default="PENDING")
    payment_date = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    # Additional details
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    receipt_number = models.CharField(max_length=100, blank=True)

    # Processing info
    processed_by = models.CharField(max_length=100, blank=True)
    verification_status = models.CharField(max_length=20, default="PENDING")

    # Refund details
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    refund_reason = models.TextField(blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "payments"
        indexes = [
            models.Index(fields=["student_fee"]),
            models.Index(fields=["status"]),
            models.Index(fields=["payment_date"]),
            models.Index(fields=["payment_method"]),
            models.Index(fields=["gateway_transaction_id"]),
            models.Index(fields=["receipt_number"]),
        ]
        ordering = ["-payment_date"]

    def __str__(self):
        return f"Payment {self.receipt_number} - {self.amount} {self.currency}"


class Fine(models.Model):
    """Model for managing fines and penalties"""

    FINE_TYPES = [
        ("LATE_FEE", "Late Fee"),
        ("LIBRARY", "Library Fine"),
        ("DISCIPLINARY", "Disciplinary Fine"),
        ("DAMAGE", "Damage Fine"),
        ("LOST_ITEM", "Lost Item Fine"),
        ("HOSTEL", "Hostel Fine"),
        ("TRANSPORT", "Transport Fine"),
        ("OTHER", "Other Fine"),
    ]

    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("PAID", "Paid"),
        ("WAIVED", "Waived"),
        ("CANCELLED", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Student info
    student_id = models.CharField(max_length=100)
    student_name = models.CharField(max_length=200)
    student_email = models.EmailField()

    # Fine details
    fine_type = models.CharField(max_length=20, choices=FINE_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="INR")

    # Status and timing
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ACTIVE")
    issued_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField()
    paid_date = models.DateTimeField(null=True, blank=True)

    # Issuing authority
    issued_by = models.CharField(max_length=100)
    issuer_name = models.CharField(max_length=200)
    department = models.CharField(max_length=100, blank=True)

    # Payment tracking
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Waiver details
    waiver_reason = models.TextField(blank=True)
    waived_by = models.CharField(max_length=100, blank=True)
    waived_at = models.DateTimeField(null=True, blank=True)

    # Additional details
    reference_id = models.CharField(
        max_length=100, blank=True
    )  # Reference to related entity
    attachments = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "fines"
        indexes = [
            models.Index(fields=["student_id"]),
            models.Index(fields=["fine_type"]),
            models.Index(fields=["status"]),
            models.Index(fields=["due_date"]),
            models.Index(fields=["issued_date"]),
        ]
        ordering = ["-issued_date"]

    def __str__(self):
        return f"{self.title} - {self.student_name} ({self.amount})"

    def save(self, *args, **kwargs):
        self.balance_amount = self.amount - self.paid_amount
        super().save(*args, **kwargs)


class FinePayment(models.Model):
    """Model for fine payments"""

    PAYMENT_METHODS = [
        ("CASH", "Cash"),
        ("CARD", "Credit/Debit Card"),
        ("NET_BANKING", "Net Banking"),
        ("UPI", "UPI"),
        ("WALLET", "Digital Wallet"),
        ("CHEQUE", "Cheque"),
        ("DD", "Demand Draft"),
        ("BANK_TRANSFER", "Bank Transfer"),
    ]

    PAYMENT_STATUS = [
        ("PENDING", "Pending"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
        ("CANCELLED", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fine = models.ForeignKey(
        Fine, on_delete=models.CASCADE, related_name="fine_payments"
    )

    # Payment details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default="PENDING")

    # Payment tracking
    payment_date = models.DateTimeField(auto_now_add=True)
    reference_number = models.CharField(max_length=100, blank=True)
    receipt_number = models.CharField(max_length=100, blank=True)

    # Processing info
    processed_by = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "fine_payments"
        indexes = [
            models.Index(fields=["fine"]),
            models.Index(fields=["status"]),
            models.Index(fields=["payment_date"]),
        ]
        ordering = ["-payment_date"]

    def __str__(self):
        return f"Fine Payment {self.receipt_number} - {self.amount}"


class Transaction(models.Model):
    """Model for all financial transactions"""

    TRANSACTION_TYPES = [
        ("FEE_PAYMENT", "Fee Payment"),
        ("FINE_PAYMENT", "Fine Payment"),
        ("REFUND", "Refund"),
        ("SCHOLARSHIP", "Scholarship"),
        ("DISCOUNT", "Discount"),
        ("ADJUSTMENT", "Adjustment"),
    ]

    TRANSACTION_STATUS = [
        ("PENDING", "Pending"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
        ("CANCELLED", "Cancelled"),
        ("REVERSED", "Reversed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Transaction details
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="INR")
    description = models.TextField()

    # Parties involved
    student_id = models.CharField(max_length=100)
    student_name = models.CharField(max_length=200)

    # References
    reference_type = models.CharField(max_length=50)  # 'student_fee', 'fine', etc.
    reference_id = models.CharField(max_length=100)  # ID of the referenced object
    payment_id = models.CharField(max_length=100, blank=True)  # Related payment ID

    # Status and timing
    status = models.CharField(
        max_length=20, choices=TRANSACTION_STATUS, default="PENDING"
    )
    transaction_date = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    # Processing info
    processed_by = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    # Accounting
    debit_account = models.CharField(max_length=100, blank=True)
    credit_account = models.CharField(max_length=100, blank=True)

    # Additional metadata
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "transactions"
        indexes = [
            models.Index(fields=["student_id"]),
            models.Index(fields=["transaction_type"]),
            models.Index(fields=["status"]),
            models.Index(fields=["transaction_date"]),
            models.Index(fields=["reference_type", "reference_id"]),
        ]
        ordering = ["-transaction_date"]

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} {self.currency} ({self.student_name})"


class Invoice(models.Model):
    """Model for generating invoices"""

    INVOICE_STATUS = [
        ("DRAFT", "Draft"),
        ("SENT", "Sent"),
        ("PAID", "Paid"),
        ("OVERDUE", "Overdue"),
        ("CANCELLED", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice_number = models.CharField(max_length=50, unique=True)

    # Student info
    student_id = models.CharField(max_length=100)
    student_name = models.CharField(max_length=200)
    student_email = models.EmailField()
    billing_address = models.TextField(blank=True)

    # Invoice details
    invoice_date = models.DateField(auto_now_add=True)
    due_date = models.DateField()

    # Amounts
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Status
    status = models.CharField(max_length=20, choices=INVOICE_STATUS, default="DRAFT")

    # Line items
    line_items = models.JSONField(default=list)  # List of invoice line items

    # Additional details
    notes = models.TextField(blank=True)
    terms_and_conditions = models.TextField(blank=True)

    # Metadata
    created_by = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "invoices"
        indexes = [
            models.Index(fields=["student_id"]),
            models.Index(fields=["invoice_number"]),
            models.Index(fields=["status"]),
            models.Index(fields=["due_date"]),
            models.Index(fields=["invoice_date"]),
        ]
        ordering = ["-invoice_date"]

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.student_name}"

    def save(self, *args, **kwargs):
        # Generate invoice number if not provided
        if not self.invoice_number:
            self.invoice_number = self._generate_invoice_number()

        # Calculate balance
        self.balance_amount = self.total_amount - self.paid_amount

        # Update status based on payment
        if self.paid_amount >= self.total_amount:
            self.status = "PAID"
        elif self.due_date < timezone.now().date() and self.status != "PAID":
            self.status = "OVERDUE"

        super().save(*args, **kwargs)

    def _generate_invoice_number(self):
        """Generate unique invoice number"""
        from datetime import datetime

        year = datetime.now().year
        month = datetime.now().month

        # Get the count of invoices for this month
        count = (
            Invoice.objects.filter(
                invoice_date__year=year, invoice_date__month=month
            ).count()
            + 1
        )

        return f"INV-{year}{month:02d}-{count:04d}"


class FinancialReport(models.Model):
    """Model for storing financial reports"""

    REPORT_TYPES = [
        ("DAILY", "Daily Report"),
        ("WEEKLY", "Weekly Report"),
        ("MONTHLY", "Monthly Report"),
        ("QUARTERLY", "Quarterly Report"),
        ("ANNUAL", "Annual Report"),
        ("CUSTOM", "Custom Report"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    title = models.CharField(max_length=200)

    # Report period
    start_date = models.DateField()
    end_date = models.DateField()

    # Report data
    total_collections = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_outstanding = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_fines = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_refunds = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Detailed data
    report_data = models.JSONField(default=dict)  # Detailed report data
    summary = models.JSONField(default=dict)  # Summary statistics

    # Metadata
    generated_by = models.CharField(max_length=100)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "financial_reports"
        indexes = [
            models.Index(fields=["report_type"]),
            models.Index(fields=["start_date", "end_date"]),
            models.Index(fields=["generated_at"]),
        ]
        ordering = ["-generated_at"]

    def __str__(self):
        return f"{self.title} ({self.start_date} to {self.end_date})"
