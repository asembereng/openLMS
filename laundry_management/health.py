"""
Health check views for openLMS
"""
from django.http import JsonResponse
from django.db import connections
from django.core.cache import cache
import time


def health_check(request):
    """Health check endpoint for container monitoring"""
    try:
        # Check database connection
        db_conn = connections['default']
        db_conn.cursor()
        
        # Check cache (if configured)
        try:
            cache_key = f'health_check_{int(time.time())}'
            cache.set(cache_key, 'ok', 10)
            cache.get(cache_key)
            cache_status = 'ok'
        except Exception:
            cache_status = 'disabled'
        
        return JsonResponse({
            'status': 'healthy',
            'database': 'ok',
            'cache': cache_status,
            'timestamp': time.time(),
            'app': 'openLMS'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': time.time(),
            'app': 'openLMS'
        }, status=503)
