from django.urls import path
from . import views

urlpatterns = [
    path('status/', views.gateway_status, name='gateway-status'),
    path('routes/', views.service_routes, name='service-routes'),
]
