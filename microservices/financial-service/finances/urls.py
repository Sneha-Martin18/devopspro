from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (FeeStructureViewSet, FinancialReportViewSet,
                    FinePaymentViewSet, FineViewSet, InvoiceViewSet,
                    PaymentViewSet, StudentFeeViewSet, TransactionViewSet)

router = DefaultRouter()
router.register(r"fee-structures", FeeStructureViewSet)
router.register(r"student-fees", StudentFeeViewSet)
router.register(r"payments", PaymentViewSet)
router.register(r"fines", FineViewSet)
router.register(r"fine-payments", FinePaymentViewSet)
router.register(r"transactions", TransactionViewSet)
router.register(r"invoices", InvoiceViewSet)
router.register(r"reports", FinancialReportViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
