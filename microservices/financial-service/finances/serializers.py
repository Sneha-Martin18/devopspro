from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from .models import (FeeStructure, FinancialReport, Fine, FinePayment, Invoice,
                     Payment, StudentFee, Transaction)


class FeeStructureSerializer(serializers.ModelSerializer):
    """Serializer for FeeStructure model"""

    class Meta:
        model = FeeStructure
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value

    def validate_late_fee_percentage(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError(
                "Late fee percentage must be between 0 and 100"
            )
        return value

    def validate_max_installments(self, value):
        if value < 1:
            raise serializers.ValidationError("Maximum installments must be at least 1")
        return value


class StudentFeeSerializer(serializers.ModelSerializer):
    """Serializer for StudentFee model"""

    fee_structure_details = FeeStructureSerializer(
        source="fee_structure", read_only=True
    )
    payment_history = serializers.SerializerMethodField()

    class Meta:
        model = StudentFee
        fields = "__all__"
        read_only_fields = (
            "id",
            "balance_amount",
            "payment_count",
            "last_payment_date",
            "created_at",
            "updated_at",
            "is_overdue",
        )

    def get_payment_history(self, obj):
        payments = obj.payments.filter(status="SUCCESS").order_by("-payment_date")[:5]
        return PaymentSerializer(payments, many=True).data

    def validate(self, data):
        if data.get("final_amount", 0) < 0:
            raise serializers.ValidationError("Final amount cannot be negative")

        if data.get("paid_amount", 0) > data.get("final_amount", 0):
            raise serializers.ValidationError("Paid amount cannot exceed final amount")

        return data


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for Payment model"""

    student_fee_details = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = "__all__"
        read_only_fields = ("id", "payment_date", "processed_at")

    def get_student_fee_details(self, obj):
        return {
            "student_name": obj.student_fee.student_name,
            "fee_type": obj.student_fee.fee_structure.fee_type,
            "fee_name": obj.student_fee.fee_structure.name,
        }

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Payment amount must be greater than 0")
        return value

    def validate(self, data):
        student_fee = data.get("student_fee")
        amount = data.get("amount", 0)

        if student_fee and amount > student_fee.balance_amount:
            raise serializers.ValidationError(
                f"Payment amount ({amount}) cannot exceed balance amount ({student_fee.balance_amount})"
            )

        return data


class FineSerializer(serializers.ModelSerializer):
    """Serializer for Fine model"""

    payment_history = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = Fine
        fields = "__all__"
        read_only_fields = ("id", "issued_date", "paid_date", "balance_amount")

    def get_payment_history(self, obj):
        payments = obj.fine_payments.filter(status="SUCCESS").order_by("-payment_date")[
            :5
        ]
        return FinePaymentSerializer(payments, many=True).data

    def get_is_overdue(self, obj):
        return obj.due_date < timezone.now().date() and obj.status == "ACTIVE"

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Fine amount must be greater than 0")
        return value


class FinePaymentSerializer(serializers.ModelSerializer):
    """Serializer for FinePayment model"""

    fine_details = serializers.SerializerMethodField()

    class Meta:
        model = FinePayment
        fields = "__all__"
        read_only_fields = ("id", "payment_date")

    def get_fine_details(self, obj):
        return {
            "fine_title": obj.fine.title,
            "fine_type": obj.fine.fine_type,
            "student_name": obj.fine.student_name,
        }

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Payment amount must be greater than 0")
        return value

    def validate(self, data):
        fine = data.get("fine")
        amount = data.get("amount", 0)

        if fine and amount > fine.balance_amount:
            raise serializers.ValidationError(
                f"Payment amount ({amount}) cannot exceed fine balance ({fine.balance_amount})"
            )

        return data


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for Transaction model"""

    class Meta:
        model = Transaction
        fields = "__all__"
        read_only_fields = ("id", "transaction_date", "processed_at")

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Transaction amount must be greater than 0"
            )
        return value


class InvoiceLineItemSerializer(serializers.Serializer):
    """Serializer for invoice line items"""

    description = serializers.CharField(max_length=200)
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")
        return value

    def validate_unit_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Unit price cannot be negative")
        return value


class InvoiceSerializer(serializers.ModelSerializer):
    """Serializer for Invoice model"""

    line_items = InvoiceLineItemSerializer(many=True)
    payment_history = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = "__all__"
        read_only_fields = (
            "id",
            "invoice_number",
            "invoice_date",
            "balance_amount",
            "created_at",
            "updated_at",
        )

    def get_payment_history(self, obj):
        # Get related payments for this invoice
        payments = Payment.objects.filter(
            gateway_order_id=str(obj.id), status="SUCCESS"
        ).order_by("-payment_date")[:5]
        return PaymentSerializer(payments, many=True).data

    def validate_line_items(self, value):
        if not value:
            raise serializers.ValidationError(
                "Invoice must have at least one line item"
            )
        return value

    def create(self, validated_data):
        line_items_data = validated_data.pop("line_items")
        invoice = Invoice.objects.create(**validated_data)

        # Calculate totals from line items
        subtotal = Decimal("0.00")
        for item_data in line_items_data:
            item_total = item_data["quantity"] * item_data["unit_price"]
            item_data["total"] = item_total
            subtotal += item_total

        invoice.line_items = line_items_data
        invoice.subtotal = subtotal
        invoice.total_amount = subtotal - invoice.discount_amount + invoice.tax_amount
        invoice.balance_amount = invoice.total_amount
        invoice.save()

        return invoice

    def update(self, instance, validated_data):
        line_items_data = validated_data.pop("line_items", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if line_items_data is not None:
            # Recalculate totals
            subtotal = Decimal("0.00")
            for item_data in line_items_data:
                item_total = item_data["quantity"] * item_data["unit_price"]
                item_data["total"] = item_total
                subtotal += item_total

            instance.line_items = line_items_data
            instance.subtotal = subtotal
            instance.total_amount = (
                subtotal - instance.discount_amount + instance.tax_amount
            )
            instance.balance_amount = instance.total_amount - instance.paid_amount

        instance.save()
        return instance


class FinancialReportSerializer(serializers.ModelSerializer):
    """Serializer for FinancialReport model"""

    class Meta:
        model = FinancialReport
        fields = "__all__"
        read_only_fields = ("id", "generated_at")

    def validate(self, data):
        if data.get("start_date") and data.get("end_date"):
            if data["start_date"] > data["end_date"]:
                raise serializers.ValidationError("Start date cannot be after end date")
        return data


# Bulk operation serializers
class BulkStudentFeeSerializer(serializers.Serializer):
    """Serializer for bulk student fee creation"""

    fee_structure_id = serializers.UUIDField()
    student_ids = serializers.ListField(
        child=serializers.CharField(max_length=100), min_length=1
    )
    discount_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    discount_reason = serializers.CharField(
        max_length=500, required=False, allow_blank=True
    )

    def validate_discount_amount(self, value):
        if value < 0:
            raise serializers.ValidationError("Discount amount cannot be negative")
        return value


class BulkPaymentSerializer(serializers.Serializer):
    """Serializer for bulk payment processing"""

    payments = serializers.ListField(child=serializers.DictField(), min_length=1)
    payment_method = serializers.ChoiceField(choices=Payment.PAYMENT_METHODS)
    processed_by = serializers.CharField(max_length=100)
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True)


# Statistics and analytics serializers
class FeeCollectionStatsSerializer(serializers.Serializer):
    """Serializer for fee collection statistics"""

    total_fees_generated = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_collected = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_outstanding = serializers.DecimalField(max_digits=15, decimal_places=2)
    collection_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)

    # Breakdown by fee type
    fee_type_breakdown = serializers.DictField()

    # Breakdown by status
    status_breakdown = serializers.DictField()

    # Monthly trends
    monthly_trends = serializers.ListField(child=serializers.DictField())


class PaymentAnalyticsSerializer(serializers.Serializer):
    """Serializer for payment analytics"""

    total_payments = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    average_payment_amount = serializers.DecimalField(max_digits=10, decimal_places=2)

    # Payment method breakdown
    payment_method_breakdown = serializers.DictField()

    # Payment gateway breakdown
    gateway_breakdown = serializers.DictField()

    # Success rate
    success_rate = serializers.DecimalField(max_digits=5, decimal_places=2)

    # Daily trends
    daily_trends = serializers.ListField(child=serializers.DictField())


class FineAnalyticsSerializer(serializers.Serializer):
    """Serializer for fine analytics"""

    total_fines = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_collected = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_outstanding = serializers.DecimalField(max_digits=15, decimal_places=2)

    # Fine type breakdown
    fine_type_breakdown = serializers.DictField()

    # Status breakdown
    status_breakdown = serializers.DictField()

    # Collection rate
    collection_rate = serializers.DecimalField(max_digits=5, decimal_places=2)


class StudentFinancialSummarySerializer(serializers.Serializer):
    """Serializer for student financial summary"""

    student_id = serializers.CharField()
    student_name = serializers.CharField()

    # Fee summary
    total_fees = serializers.DecimalField(max_digits=10, decimal_places=2)
    fees_paid = serializers.DecimalField(max_digits=10, decimal_places=2)
    fees_outstanding = serializers.DecimalField(max_digits=10, decimal_places=2)

    # Fine summary
    total_fines = serializers.DecimalField(max_digits=10, decimal_places=2)
    fines_paid = serializers.DecimalField(max_digits=10, decimal_places=2)
    fines_outstanding = serializers.DecimalField(max_digits=10, decimal_places=2)

    # Overall summary
    total_outstanding = serializers.DecimalField(max_digits=10, decimal_places=2)
    last_payment_date = serializers.DateTimeField(allow_null=True)

    # Recent transactions
    recent_transactions = TransactionSerializer(many=True)


# Payment gateway integration serializers
class PaymentGatewayRequestSerializer(serializers.Serializer):
    """Serializer for payment gateway requests"""

    student_fee_id = serializers.UUIDField(required=False)
    fine_id = serializers.UUIDField(required=False)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField(max_length=10, default="INR")
    payment_method = serializers.ChoiceField(choices=Payment.PAYMENT_METHODS)
    gateway = serializers.ChoiceField(choices=Payment.GATEWAY_CHOICES)

    # Customer details
    customer_name = serializers.CharField(max_length=200)
    customer_email = serializers.EmailField()
    customer_phone = serializers.CharField(max_length=20, required=False)

    # Additional details
    description = serializers.CharField(max_length=500, required=False)
    callback_url = serializers.URLField(required=False)

    def validate(self, data):
        if not data.get("student_fee_id") and not data.get("fine_id"):
            raise serializers.ValidationError(
                "Either student_fee_id or fine_id must be provided"
            )

        if data.get("student_fee_id") and data.get("fine_id"):
            raise serializers.ValidationError(
                "Only one of student_fee_id or fine_id should be provided"
            )

        return data


class PaymentGatewayResponseSerializer(serializers.Serializer):
    """Serializer for payment gateway responses"""

    gateway_order_id = serializers.CharField()
    gateway_payment_id = serializers.CharField(required=False)
    payment_url = serializers.URLField(required=False)
    qr_code = serializers.CharField(required=False)

    # Gateway specific data
    gateway_data = serializers.DictField()

    # Status
    status = serializers.CharField()
    message = serializers.CharField(required=False)
