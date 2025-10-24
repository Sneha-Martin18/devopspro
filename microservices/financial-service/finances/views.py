import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (FeeStructure, FinancialReport, Fine, FinePayment, Invoice,
                     Payment, StudentFee, Transaction)
from .serializers import (BulkPaymentSerializer, BulkStudentFeeSerializer,
                          FeeCollectionStatsSerializer, FeeStructureSerializer,
                          FinancialReportSerializer, FineAnalyticsSerializer,
                          FinePaymentSerializer, FineSerializer,
                          InvoiceSerializer, PaymentAnalyticsSerializer,
                          PaymentGatewayRequestSerializer,
                          PaymentGatewayResponseSerializer, PaymentSerializer,
                          StudentFeeSerializer,
                          StudentFinancialSummarySerializer,
                          TransactionSerializer)
from .tasks import (generate_invoice_task, process_payment_gateway_callback,
                    send_payment_confirmation, send_payment_reminder)

logger = logging.getLogger(__name__)


class FeeStructureViewSet(viewsets.ModelViewSet):
    """ViewSet for managing fee structures"""

    queryset = FeeStructure.objects.all()
    serializer_class = FeeStructureSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = [
        "fee_type",
        "course_id",
        "academic_year",
        "semester",
        "is_active",
        "mandatory",
    ]
    search_fields = ["name", "description", "course_name"]
    ordering_fields = ["name", "fee_type", "amount", "due_date", "created_at"]
    ordering = ["-created_at"]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user.username)

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        """Duplicate a fee structure for a new academic year/semester"""
        fee_structure = self.get_object()

        # Get new academic details from request
        new_academic_year = request.data.get("academic_year")
        new_semester = request.data.get("semester", fee_structure.semester)

        if not new_academic_year:
            return Response(
                {"error": "academic_year is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create duplicate
        fee_structure.pk = None
        fee_structure.academic_year = new_academic_year
        fee_structure.semester = new_semester
        fee_structure.created_by = request.user.username
        fee_structure.save()

        serializer = self.get_serializer(fee_structure)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def active_structures(self, request):
        """Get all active fee structures"""
        active_structures = self.queryset.filter(is_active=True)
        serializer = self.get_serializer(active_structures, many=True)
        return Response(serializer.data)


class StudentFeeViewSet(viewsets.ModelViewSet):
    """ViewSet for managing student fees"""

    queryset = StudentFee.objects.select_related("fee_structure").all()
    serializer_class = StudentFeeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["status", "student_id", "fee_structure__fee_type", "is_overdue"]
    search_fields = ["student_name", "student_email", "fee_structure__name"]
    ordering_fields = ["due_date", "final_amount", "balance_amount", "created_at"]
    ordering = ["-created_at"]

    @action(detail=False, methods=["post"])
    def bulk_create(self, request):
        """Bulk create student fees"""
        serializer = BulkStudentFeeSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    fee_structure_id = serializer.validated_data["fee_structure_id"]
                    student_ids = serializer.validated_data["student_ids"]
                    discount_amount = serializer.validated_data.get(
                        "discount_amount", 0
                    )
                    discount_reason = serializer.validated_data.get(
                        "discount_reason", ""
                    )

                    fee_structure = FeeStructure.objects.get(id=fee_structure_id)
                    created_fees = []

                    for student_id in student_ids:
                        # Check if fee already exists
                        if StudentFee.objects.filter(
                            fee_structure=fee_structure, student_id=student_id
                        ).exists():
                            continue

                        # Calculate final amount
                        final_amount = fee_structure.amount - discount_amount

                        student_fee = StudentFee.objects.create(
                            fee_structure=fee_structure,
                            student_id=student_id,
                            student_name=f"Student {student_id}",  # This should come from User Service
                            student_email=f"student{student_id}@example.com",  # This should come from User Service
                            original_amount=fee_structure.amount,
                            discount_amount=discount_amount,
                            final_amount=final_amount,
                            balance_amount=final_amount,
                            due_date=fee_structure.due_date,
                            discount_reason=discount_reason,
                        )
                        created_fees.append(student_fee)

                    serializer = StudentFeeSerializer(created_fees, many=True)
                    return Response(
                        {
                            "message": f"Created {len(created_fees)} student fees",
                            "fees": serializer.data,
                        },
                        status=status.HTTP_201_CREATED,
                    )

            except FeeStructure.DoesNotExist:
                return Response(
                    {"error": "Fee structure not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            except Exception as e:
                logger.error(f"Bulk fee creation failed: {str(e)}")
                return Response(
                    {"error": "Failed to create fees"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def apply_discount(self, request, pk=None):
        """Apply discount to a student fee"""
        student_fee = self.get_object()

        discount_amount = request.data.get("discount_amount", 0)
        discount_reason = request.data.get("discount_reason", "")

        if discount_amount < 0:
            return Response(
                {"error": "Discount amount cannot be negative"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if discount_amount > student_fee.original_amount:
            return Response(
                {"error": "Discount amount cannot exceed original amount"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        student_fee.discount_amount = discount_amount
        student_fee.discount_reason = discount_reason
        student_fee.final_amount = student_fee.original_amount - discount_amount
        student_fee.save()

        serializer = self.get_serializer(student_fee)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def waive_fee(self, request, pk=None):
        """Waive a student fee"""
        student_fee = self.get_object()

        waiver_reason = request.data.get("waiver_reason", "")
        if not waiver_reason:
            return Response(
                {"error": "Waiver reason is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        student_fee.status = "WAIVED"
        student_fee.waiver_reason = waiver_reason
        student_fee.waived_by = request.user.username
        student_fee.waived_at = timezone.now()
        student_fee.save()

        serializer = self.get_serializer(student_fee)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def overdue_fees(self, request):
        """Get all overdue fees"""
        overdue_fees = self.queryset.filter(is_overdue=True)
        serializer = self.get_serializer(overdue_fees, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def student_summary(self, request):
        """Get fee summary for a specific student"""
        student_id = request.query_params.get("student_id")
        if not student_id:
            return Response(
                {"error": "student_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        student_fees = self.queryset.filter(student_id=student_id)

        # Calculate summary
        total_fees = (
            student_fees.aggregate(Sum("final_amount"))["final_amount__sum"] or 0
        )
        fees_paid = student_fees.aggregate(Sum("paid_amount"))["paid_amount__sum"] or 0
        fees_outstanding = (
            student_fees.aggregate(Sum("balance_amount"))["balance_amount__sum"] or 0
        )

        # Get recent transactions
        recent_transactions = Transaction.objects.filter(
            student_id=student_id, transaction_type="FEE_PAYMENT"
        ).order_by("-transaction_date")[:10]

        summary_data = {
            "student_id": student_id,
            "student_name": student_fees.first().student_name
            if student_fees.exists()
            else "",
            "total_fees": total_fees,
            "fees_paid": fees_paid,
            "fees_outstanding": fees_outstanding,
            "total_fines": 0,  # Will be calculated from Fine model
            "fines_paid": 0,
            "fines_outstanding": 0,
            "total_outstanding": fees_outstanding,
            "last_payment_date": student_fees.filter(last_payment_date__isnull=False)
            .order_by("-last_payment_date")
            .first()
            .last_payment_date
            if student_fees.filter(last_payment_date__isnull=False).exists()
            else None,
            "recent_transactions": TransactionSerializer(
                recent_transactions, many=True
            ).data,
        }

        serializer = StudentFinancialSummarySerializer(summary_data)
        return Response(serializer.data)


class PaymentViewSet(viewsets.ModelViewSet):
    """ViewSet for managing payments"""

    queryset = Payment.objects.select_related("student_fee__fee_structure").all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = [
        "status",
        "payment_method",
        "payment_gateway",
        "student_fee__student_id",
    ]
    search_fields = ["gateway_transaction_id", "receipt_number", "reference_number"]
    ordering_fields = ["payment_date", "amount", "status"]
    ordering = ["-payment_date"]

    @action(detail=False, methods=["post"])
    def initiate_payment(self, request):
        """Initiate payment through gateway"""
        serializer = PaymentGatewayRequestSerializer(data=request.data)
        if serializer.is_valid():
            # This would integrate with actual payment gateways
            # For now, return a mock response
            response_data = {
                "gateway_order_id": f"order_{timezone.now().timestamp()}",
                "payment_url": "https://payment-gateway.com/pay/12345",
                "gateway_data": {
                    "order_id": f"order_{timezone.now().timestamp()}",
                    "amount": str(serializer.validated_data["amount"]),
                    "currency": serializer.validated_data["currency"],
                },
                "status": "INITIATED",
                "message": "Payment initiated successfully",
            }

            response_serializer = PaymentGatewayResponseSerializer(response_data)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def verify_payment(self, request, pk=None):
        """Verify payment with gateway"""
        payment = self.get_object()

        # This would verify with actual payment gateway
        # For now, simulate verification
        if payment.status == "PENDING":
            payment.status = "SUCCESS"
            payment.processed_at = timezone.now()
            payment.processed_by = request.user.username
            payment.save()

            # Update student fee
            student_fee = payment.student_fee
            student_fee.paid_amount += payment.amount
            student_fee.payment_count += 1
            student_fee.last_payment_date = payment.payment_date
            student_fee.save()

            # Send confirmation
            send_payment_confirmation.delay(payment.id)

        serializer = self.get_serializer(payment)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def bulk_process(self, request):
        """Bulk process payments"""
        serializer = BulkPaymentSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    payments_data = serializer.validated_data["payments"]
                    payment_method = serializer.validated_data["payment_method"]
                    processed_by = serializer.validated_data["processed_by"]
                    notes = serializer.validated_data.get("notes", "")

                    processed_payments = []

                    for payment_data in payments_data:
                        payment = Payment.objects.get(id=payment_data["payment_id"])
                        payment.status = "SUCCESS"
                        payment.payment_method = payment_method
                        payment.processed_by = processed_by
                        payment.processed_at = timezone.now()
                        payment.notes = notes
                        payment.save()

                        # Update related student fee
                        student_fee = payment.student_fee
                        student_fee.paid_amount += payment.amount
                        student_fee.payment_count += 1
                        student_fee.last_payment_date = payment.payment_date
                        student_fee.save()

                        processed_payments.append(payment)

                    serializer = PaymentSerializer(processed_payments, many=True)
                    return Response(
                        {
                            "message": f"Processed {len(processed_payments)} payments",
                            "payments": serializer.data,
                        }
                    )

            except Payment.DoesNotExist:
                return Response(
                    {"error": "One or more payments not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            except Exception as e:
                logger.error(f"Bulk payment processing failed: {str(e)}")
                return Response(
                    {"error": "Failed to process payments"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"])
    def analytics(self, request):
        """Get payment analytics"""
        # Date range filtering
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        queryset = self.queryset.filter(status="SUCCESS")
        if start_date:
            queryset = queryset.filter(payment_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(payment_date__lte=end_date)

        # Calculate analytics
        total_payments = queryset.count()
        total_amount = queryset.aggregate(Sum("amount"))["amount__sum"] or 0
        average_amount = queryset.aggregate(Avg("amount"))["amount__avg"] or 0

        # Payment method breakdown
        method_breakdown = {}
        for method, _ in Payment.PAYMENT_METHODS:
            count = queryset.filter(payment_method=method).count()
            amount = (
                queryset.filter(payment_method=method).aggregate(Sum("amount"))[
                    "amount__sum"
                ]
                or 0
            )
            method_breakdown[method] = {"count": count, "amount": float(amount)}

        # Gateway breakdown
        gateway_breakdown = {}
        for gateway, _ in Payment.GATEWAY_CHOICES:
            count = queryset.filter(payment_gateway=gateway).count()
            amount = (
                queryset.filter(payment_gateway=gateway).aggregate(Sum("amount"))[
                    "amount__sum"
                ]
                or 0
            )
            gateway_breakdown[gateway] = {"count": count, "amount": float(amount)}

        # Success rate (including failed payments)
        all_payments = self.queryset
        if start_date:
            all_payments = all_payments.filter(payment_date__gte=start_date)
        if end_date:
            all_payments = all_payments.filter(payment_date__lte=end_date)

        total_attempts = all_payments.count()
        success_rate = (
            (total_payments / total_attempts * 100) if total_attempts > 0 else 0
        )

        analytics_data = {
            "total_payments": total_payments,
            "total_amount": total_amount,
            "average_payment_amount": average_amount,
            "payment_method_breakdown": method_breakdown,
            "gateway_breakdown": gateway_breakdown,
            "success_rate": success_rate,
            "daily_trends": [],  # This would be calculated based on requirements
        }

        serializer = PaymentAnalyticsSerializer(analytics_data)
        return Response(serializer.data)


class FineViewSet(viewsets.ModelViewSet):
    """ViewSet for managing fines"""

    queryset = Fine.objects.all()
    serializer_class = FineSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["fine_type", "status", "student_id", "issued_by"]
    search_fields = ["title", "description", "student_name", "student_email"]
    ordering_fields = ["issued_date", "due_date", "amount"]
    ordering = ["-issued_date"]

    def perform_create(self, serializer):
        serializer.save(
            issued_by=self.request.user.username,
            issuer_name=getattr(
                self.request.user, "get_full_name", lambda: self.request.user.username
            )(),
        )

    @action(detail=True, methods=["post"])
    def waive_fine(self, request, pk=None):
        """Waive a fine"""
        fine = self.get_object()

        waiver_reason = request.data.get("waiver_reason", "")
        if not waiver_reason:
            return Response(
                {"error": "Waiver reason is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        fine.status = "WAIVED"
        fine.waiver_reason = waiver_reason
        fine.waived_by = request.user.username
        fine.waived_at = timezone.now()
        fine.save()

        serializer = self.get_serializer(fine)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def overdue_fines(self, request):
        """Get all overdue fines"""
        overdue_fines = self.queryset.filter(
            due_date__lt=timezone.now().date(), status="ACTIVE"
        )
        serializer = self.get_serializer(overdue_fines, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def analytics(self, request):
        """Get fine analytics"""
        # Date range filtering
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        queryset = self.queryset
        if start_date:
            queryset = queryset.filter(issued_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(issued_date__lte=end_date)

        # Calculate analytics
        total_fines = queryset.count()
        total_amount = queryset.aggregate(Sum("amount"))["amount__sum"] or 0
        total_collected = (
            queryset.aggregate(Sum("paid_amount"))["paid_amount__sum"] or 0
        )
        total_outstanding = (
            queryset.aggregate(Sum("balance_amount"))["balance_amount__sum"] or 0
        )

        # Fine type breakdown
        type_breakdown = {}
        for fine_type, _ in Fine.FINE_TYPES:
            count = queryset.filter(fine_type=fine_type).count()
            amount = (
                queryset.filter(fine_type=fine_type).aggregate(Sum("amount"))[
                    "amount__sum"
                ]
                or 0
            )
            type_breakdown[fine_type] = {"count": count, "amount": float(amount)}

        # Status breakdown
        status_breakdown = {}
        for status_choice, _ in Fine.STATUS_CHOICES:
            count = queryset.filter(status=status_choice).count()
            amount = (
                queryset.filter(status=status_choice).aggregate(Sum("amount"))[
                    "amount__sum"
                ]
                or 0
            )
            status_breakdown[status_choice] = {"count": count, "amount": float(amount)}

        # Collection rate
        collection_rate = (
            (total_collected / total_amount * 100) if total_amount > 0 else 0
        )

        analytics_data = {
            "total_fines": total_fines,
            "total_amount": total_amount,
            "total_collected": total_collected,
            "total_outstanding": total_outstanding,
            "fine_type_breakdown": type_breakdown,
            "status_breakdown": status_breakdown,
            "collection_rate": collection_rate,
        }

        serializer = FineAnalyticsSerializer(analytics_data)
        return Response(serializer.data)


class FinePaymentViewSet(viewsets.ModelViewSet):
    """ViewSet for managing fine payments"""

    queryset = FinePayment.objects.select_related("fine").all()
    serializer_class = FinePaymentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["status", "payment_method", "fine__student_id"]
    search_fields = ["reference_number", "receipt_number"]
    ordering_fields = ["payment_date", "amount"]
    ordering = ["-payment_date"]

    def perform_create(self, serializer):
        payment = serializer.save(processed_by=self.request.user.username)

        # Update fine
        fine = payment.fine
        fine.paid_amount += payment.amount
        if fine.paid_amount >= fine.amount:
            fine.status = "PAID"
            fine.paid_date = timezone.now()
        fine.save()


class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing transactions (read-only)"""

    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["transaction_type", "status", "student_id", "reference_type"]
    search_fields = ["description", "student_name", "reference_id"]
    ordering_fields = ["transaction_date", "amount"]
    ordering = ["-transaction_date"]


class InvoiceViewSet(viewsets.ModelViewSet):
    """ViewSet for managing invoices"""

    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["status", "student_id"]
    search_fields = ["invoice_number", "student_name", "student_email"]
    ordering_fields = ["invoice_date", "due_date", "total_amount"]
    ordering = ["-invoice_date"]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user.username)

    @action(detail=True, methods=["post"])
    def send_invoice(self, request, pk=None):
        """Send invoice to student"""
        invoice = self.get_object()

        if invoice.status == "DRAFT":
            invoice.status = "SENT"
            invoice.save()

        # Send invoice via email (async task)
        generate_invoice_task.delay(invoice.id, send_email=True)

        return Response({"message": "Invoice sent successfully"})

    @action(detail=True, methods=["post"])
    def mark_paid(self, request, pk=None):
        """Mark invoice as paid"""
        invoice = self.get_object()

        payment_amount = request.data.get("payment_amount", invoice.balance_amount)
        payment_method = request.data.get("payment_method", "MANUAL")

        invoice.paid_amount += Decimal(str(payment_amount))
        if invoice.paid_amount >= invoice.total_amount:
            invoice.status = "PAID"

        invoice.save()

        # Create transaction record
        Transaction.objects.create(
            transaction_type="FEE_PAYMENT",
            amount=payment_amount,
            description=f"Payment for invoice {invoice.invoice_number}",
            student_id=invoice.student_id,
            student_name=invoice.student_name,
            reference_type="invoice",
            reference_id=str(invoice.id),
            status="COMPLETED",
            processed_by=request.user.username,
            processed_at=timezone.now(),
        )

        serializer = self.get_serializer(invoice)
        return Response(serializer.data)


class FinancialReportViewSet(viewsets.ModelViewSet):
    """ViewSet for managing financial reports"""

    queryset = FinancialReport.objects.all()
    serializer_class = FinancialReportSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["report_type"]
    search_fields = ["title"]
    ordering_fields = ["generated_at", "start_date", "end_date"]
    ordering = ["-generated_at"]

    def perform_create(self, serializer):
        serializer.save(generated_by=self.request.user.username)

    @action(detail=False, methods=["post"])
    def generate_report(self, request):
        """Generate a financial report"""
        report_type = request.data.get("report_type", "CUSTOM")
        start_date = request.data.get("start_date")
        end_date = request.data.get("end_date")
        title = request.data.get("title", f"{report_type} Financial Report")

        if not start_date or not end_date:
            return Response(
                {"error": "start_date and end_date are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Calculate report data
        # Fee collections
        fee_collections = (
            StudentFee.objects.filter(
                last_payment_date__range=[start_date, end_date]
            ).aggregate(Sum("paid_amount"))["paid_amount__sum"]
            or 0
        )

        # Outstanding fees
        outstanding_fees = (
            StudentFee.objects.filter(balance_amount__gt=0).aggregate(
                Sum("balance_amount")
            )["balance_amount__sum"]
            or 0
        )

        # Fine collections
        fine_collections = (
            Fine.objects.filter(paid_date__range=[start_date, end_date]).aggregate(
                Sum("paid_amount")
            )["paid_amount__sum"]
            or 0
        )

        # Create report
        report = FinancialReport.objects.create(
            report_type=report_type,
            title=title,
            start_date=start_date,
            end_date=end_date,
            total_collections=fee_collections + fine_collections,
            total_outstanding=outstanding_fees,
            total_fines=fine_collections,
            generated_by=request.user.username,
            report_data={
                "fee_collections": float(fee_collections),
                "fine_collections": float(fine_collections),
                "outstanding_fees": float(outstanding_fees),
                "period": f"{start_date} to {end_date}",
            },
        )

        serializer = self.get_serializer(report)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def dashboard_stats(self, request):
        """Get dashboard statistics"""
        # Today's collections
        today = timezone.now().date()
        today_collections = (
            Payment.objects.filter(
                payment_date__date=today, status="SUCCESS"
            ).aggregate(Sum("amount"))["amount__sum"]
            or 0
        )

        # This month's collections
        this_month = today.replace(day=1)
        month_collections = (
            Payment.objects.filter(
                payment_date__date__gte=this_month, status="SUCCESS"
            ).aggregate(Sum("amount"))["amount__sum"]
            or 0
        )

        # Total outstanding
        total_outstanding = (
            StudentFee.objects.filter(balance_amount__gt=0).aggregate(
                Sum("balance_amount")
            )["balance_amount__sum"]
            or 0
        )

        # Overdue fees
        overdue_amount = (
            StudentFee.objects.filter(is_overdue=True).aggregate(Sum("balance_amount"))[
                "balance_amount__sum"
            ]
            or 0
        )

        stats = {
            "today_collections": float(today_collections),
            "month_collections": float(month_collections),
            "total_outstanding": float(total_outstanding),
            "overdue_amount": float(overdue_amount),
            "pending_payments": Payment.objects.filter(status="PENDING").count(),
            "active_fines": Fine.objects.filter(status="ACTIVE").count(),
        }

        return Response(stats)
