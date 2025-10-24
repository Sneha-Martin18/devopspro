from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .config import (
    SERVICE_ROUTES, 
    ACADEMIC_SERVICES, 
    ADMIN_SERVICES, 
    USER_SERVICES, 
    FINANCIAL_SERVICES
)

def index(request):
    """Gateway home page showing available services"""
    return JsonResponse({
        'message': 'Student Management System Gateway',
        'status': 'active',
        'available_services': list(SERVICE_ROUTES.keys())
    })

@require_http_methods(["GET"])
def gateway_status(request):
    """Return the status of all services"""
    services_status = {
        'academic_services': {
            'name': 'Academic Services',
            'endpoints': ACADEMIC_SERVICES,
            'status': 'active'
        },
        'admin_services': {
            'name': 'Administrative Services',
            'endpoints': ADMIN_SERVICES,
            'status': 'active'
        },
        'user_services': {
            'name': 'User Services',
            'endpoints': USER_SERVICES,
            'status': 'active'
        },
        'financial_services': {
            'name': 'Financial Services',
            'endpoints': FINANCIAL_SERVICES,
            'status': 'active'
        }
    }
    
    return JsonResponse({
        'gateway_status': 'operational',
        'services': services_status,
        'version': '1.0.0'
    })

@require_http_methods(["GET"])
def list_services(request):
    """List all available services and their endpoints"""
    return JsonResponse({
        'services': {
            'academic': {
                'description': 'Academic related services',
                'endpoints': ACADEMIC_SERVICES
            },
            'administrative': {
                'description': 'Administrative services',
                'endpoints': ADMIN_SERVICES
            },
            'user_management': {
                'description': 'User management services',
                'endpoints': USER_SERVICES
            },
            'financial': {
                'description': 'Financial services',
                'endpoints': FINANCIAL_SERVICES
            }
        }
    })

@require_http_methods(["GET"])
def service_routes(request):
    """Return all available service routes"""
    return JsonResponse({
        'available_routes': SERVICE_ROUTES
    })
