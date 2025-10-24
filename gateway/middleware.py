import requests
import logging
from django.http import JsonResponse, HttpResponse
from django.core.cache import cache
from .config import (
    SERVICE_ROUTES, DEFAULT_TIMEOUT, ACADEMIC_SERVICES,
    ADMIN_SERVICES, USER_SERVICES, FINANCIAL_SERVICES,
    ENABLE_CACHING, ENABLE_RATE_LIMITING, ENABLE_AUTH_CHECK
)

logger = logging.getLogger(__name__)

class GatewayMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def _check_auth(self, request):
        """Check if user is authenticated for protected routes"""
        if not request.user.is_authenticated:
            protected_services = ADMIN_SERVICES + FINANCIAL_SERVICES
            service = request.path.lstrip('/').split('/')[0]
            if service in protected_services:
                return False
        return True

    def _should_cache(self, request):
        """Determine if response should be cached"""
        if not ENABLE_CACHING:
            return False
        return request.method in ['GET'] and not request.path.startswith('/api/')

    def _get_cached_response(self, cache_key):
        """Get cached response if available"""
        cached_data = cache.get(cache_key)
        if cached_data:
            return JsonResponse(cached_data['data'], status=cached_data['status'])
        return None

    def _cache_response(self, cache_key, response_data, status):
        """Cache the response"""
        cache.set(cache_key, {
            'data': response_data,
            'status': status
        }, timeout=300)  # Cache for 5 minutes

    def __call__(self, request):
        path = request.path.lstrip('/')
        service = path.split('/')[0]

        # Check if service exists
        if service not in SERVICE_ROUTES:
            return self.get_response(request)

        # Auth check for protected routes
        if ENABLE_AUTH_CHECK and not self._check_auth(request):
            return JsonResponse({'error': 'Authentication required'}, status=401)

        # Rate limiting
        if ENABLE_RATE_LIMITING:
            rate_key = f"rate_limit:{request.META.get('REMOTE_ADDR')}:{service}"
            request_count = cache.get(rate_key, 0)
            if request_count > 100:  # 100 requests per minute
                return JsonResponse({'error': 'Rate limit exceeded'}, status=429)
            cache.set(rate_key, request_count + 1, timeout=60)

        # Check cache
        cache_key = f"gateway:{request.method}:{request.path}"
        if self._should_cache(request):
            cached_response = self._get_cached_response(cache_key)
            if cached_response:
                return cached_response

        try:
            # Construct service URL
            service_url = f"{SERVICE_ROUTES[service]}/{'/'.join(path.split('/')[1:])}"
            
            # Forward the request
            response = requests.request(
                method=request.method,
                url=service_url,
                headers={
                    key: value for key, value in request.headers.items()
                    if key.lower() not in ['host']
                },
                data=request.body if request.body else None,
                cookies=request.COOKIES,
                timeout=DEFAULT_TIMEOUT
            )

            # Handle different response types
            if 'application/json' in response.headers.get('Content-Type', ''):
                response_data = response.json() if response.content else {}
                if self._should_cache(request):
                    self._cache_response(cache_key, response_data, response.status_code)
                return JsonResponse(response_data, status=response.status_code)
            else:
                # For non-JSON responses (e.g., files, PDFs)
                django_response = HttpResponse(
                    content=response.content,
                    status=response.status_code,
                    content_type=response.headers.get('Content-Type')
                )
                # Copy relevant headers
                for header, value in response.headers.items():
                    if header.lower() not in ['content-length', 'content-encoding']:
                        django_response[header] = value
                return django_response

        except requests.RequestException as e:
            logger.error(f"Gateway error for {service}: {str(e)}")
            return JsonResponse(
                {'error': 'Service temporarily unavailable'},
                status=503
            )
        except Exception as e:
            logger.error(f"Unexpected error in gateway: {str(e)}")
            return JsonResponse(
                {'error': 'Internal server error'},
                status=500
            )

        return self.get_response(request)
