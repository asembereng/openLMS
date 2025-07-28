"""
Test views for error handling functionality.
These views are used to test custom error pages in development.
"""
from django.shortcuts import render
from django.http import Http404, HttpResponseBadRequest
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


def test_400_error(request):
    """Test view to trigger a 400 Bad Request error."""
    # Suppress unused argument warning - request parameter is required by Django
    _ = request
    return HttpResponseBadRequest("This is a test 400 error for testing error handling.")


def test_403_error(request):
    """Test view to trigger a 403 Forbidden error."""
    # Suppress unused argument warning
    _ = request
    raise PermissionDenied("This is a test 403 error for testing error handling.")


def test_404_error(request):
    """Test view to trigger a 404 Not Found error."""
    # Suppress unused argument warning
    _ = request
    raise Http404("This is a test 404 error for testing error handling.")


def test_500_error(request):
    """Test view to trigger a 500 Internal Server Error."""
    # Suppress unused argument warning
    _ = request
    # Intentionally cause an error
    raise ValueError("This is a test 500 error for testing error handling.")


@csrf_exempt
@require_http_methods(["POST"])
def test_csrf_error(request):
    """Test view to potentially trigger CSRF errors."""
    # This view is CSRF exempt, but can be used to test CSRF failures
    # by removing the decorator and making POST requests without CSRF tokens
    return render(request, 'test_csrf_form.html')


def error_test_dashboard(request):
    """Dashboard to test all error types."""
    context = {
        'title': 'Error Testing Dashboard',
        'subtitle': 'Test custom error pages'
    }
    return render(request, 'errors/test_dashboard.html', context)
