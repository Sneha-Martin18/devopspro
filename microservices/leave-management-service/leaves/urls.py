from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"types", views.LeaveTypeViewSet)
router.register(r"requests", views.LeaveRequestViewSet)
router.register(r"balances", views.LeaveBalanceViewSet)
router.register(r"approvals", views.LeaveApprovalViewSet)
router.register(r"policies", views.LeavePolicyViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
