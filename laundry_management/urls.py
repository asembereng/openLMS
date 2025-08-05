"""
A&F Laundry Services - URL Configuration
Laundry Management System
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView, TemplateView
from django.http import JsonResponse
from .search_views import global_search_api
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

def health_check(request):
    """Health check endpoint for load balancers"""
    # Suppress unused argument warning - request parameter is required by Django
    _ = request
    return JsonResponse({"status": "healthy", "service": "A&F Laundry Management"})

# Admin URL (configurable for security)
admin_url = getattr(settings, 'ADMIN_URL', 'admin/')

urlpatterns = [
    # Health check
    path('health/', health_check, name='health_check'),
    
    # Admin
    path(admin_url, admin.site.urls),
    
    # Authentication (allauth)
    path('accounts/auth/', include('allauth.urls')),
    
    # Legacy login URL redirects
    path('accounts/login/', RedirectView.as_view(url='/accounts/auth/login/', permanent=False)),
    path('accounts/logout/', RedirectView.as_view(url='/accounts/auth/logout/', permanent=False)),
    path('accounts/password/reset/', RedirectView.as_view(url='/accounts/auth/password/reset/', permanent=False)),
    
    # Global search API
    path('api/global-search/', global_search_api, name='global_search_api'),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('api/', TemplateView.as_view(template_name='api_docs_portal.html'), name='api_portal'),
    
    # App URLs
    path('customers/', include('customers.urls')),
    path('services/', include('services.urls')),
    path('orders/', include('orders.urls')),
    path('expenses/', include('expenses.urls')),
    path('reports/', include('reports.urls')),
    path('admin-settings/', include('system_settings.urls')),
    
    # Account management
    path('accounts/', include('accounts.urls')),
    
    # Loyalty app
    path('loyalty/', include('loyalty.urls', namespace='loyalty')),
    
    # Main dashboard
    path('', RedirectView.as_view(url='/dashboard/', permanent=False)),
    path('dashboard/', include('accounts.urls', namespace='dashboard')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Debug toolbar
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]
    
    # Error testing views (development only)
    from . import test_error_views
    urlpatterns += [
        path('test-errors/', test_error_views.error_test_dashboard, name='error_test_dashboard'),
        path('test-errors/400/', test_error_views.test_400_error, name='test_400_error'),
        path('test-errors/403/', test_error_views.test_403_error, name='test_403_error'),
        path('test-errors/404/', test_error_views.test_404_error, name='test_404_error'),
        path('test-errors/500/', test_error_views.test_500_error, name='test_500_error'),
    ]

# Custom admin site headers
admin.site.site_header = "A&F Laundry Services"
admin.site.site_title = "Laundry Management"
admin.site.index_title = "Administration Portal"

# Configure custom error handlers
handler400 = 'laundry_management.error_handlers.handler400'
handler403 = 'laundry_management.error_handlers.handler403'
handler404 = 'laundry_management.error_handlers.handler404'
handler500 = 'laundry_management.error_handlers.handler500'
csrf_failure_view = 'laundry_management.error_handlers.csrf_failure'
