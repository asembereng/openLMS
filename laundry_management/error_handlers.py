"""
Custom error handlers for the Laundry Management System.
Provides user-friendly error pages with actionable information.
"""
import logging
import uuid
from django.shortcuts import render
from django.conf import settings
from django.core.mail import mail_admins
from django.utils import timezone

logger = logging.getLogger(__name__)


def handler400(request, exception=None):
    """Handle 400 Bad Request errors."""
    # Suppress unused argument warning - exception parameter required by Django
    _ = exception
    
    context = {
        'error_code': 400,
        'error_title': 'Bad Request',
        'user': request.user if hasattr(request, 'user') else None,
    }
    
    # Log the error for debugging
    logger.warning("400 Bad Request: %s - User: %s", 
                  request.path, 
                  getattr(request.user, 'username', 'Anonymous'))
    
    response = render(request, 'errors/400.html', context)
    response.status_code = 400
    return response


def handler403(request, exception=None):
    """Handle 403 Forbidden errors."""
    # Suppress unused argument warning - exception parameter required by Django
    _ = exception
    
    context = {
        'error_code': 403,
        'error_title': 'Access Denied',
        'user': request.user if hasattr(request, 'user') else None,
    }
    
    # Log the error for security monitoring
    user_info = getattr(request.user, 'username', 'Anonymous')
    logger.warning("403 Forbidden: %s - User: %s - IP: %s", 
                  request.path, user_info, get_client_ip(request))
    
    response = render(request, 'errors/403.html', context)
    response.status_code = 403
    return response


def handler404(request, exception=None):
    """Handle 404 Not Found errors."""
    # Suppress unused argument warning - exception parameter required by Django
    _ = exception
    
    context = {
        'error_code': 404,
        'error_title': 'Page Not Found',
        'user': request.user if hasattr(request, 'user') else None,
        'requested_path': request.path,
    }
    
    # Log 404s for monitoring broken links
    logger.info("404 Not Found: %s - Referrer: %s", 
               request.path, request.META.get('HTTP_REFERER', 'Direct'))
    
    response = render(request, 'errors/404.html', context)
    response.status_code = 404
    return response


def handler500(request):
    """Handle 500 Internal Server Error."""
    # Generate unique error ID for tracking
    error_id = str(uuid.uuid4())[:8]
    timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
    
    context = {
        'error_code': 500,
        'error_title': 'Server Error',
        'error_id': error_id,
        'timestamp': timestamp,
        'user': getattr(request, 'user', None),
    }
    
    # Log the error with full details
    user_info = getattr(request.user, 'username', 'Anonymous') if hasattr(request, 'user') else 'Anonymous'
    error_details = f"""
    Error ID: {error_id}
    Path: {request.path}
    Method: {request.method}
    User: {user_info}
    IP: {get_client_ip(request)}
    User Agent: {request.META.get('HTTP_USER_AGENT', 'Unknown')}
    Time: {timestamp}
    """
    
    logger.error("500 Internal Server Error: %s", error_details)
    
    # Send email notification to admins if in production
    if not settings.DEBUG:
        try:
            mail_admins(
                subject=f'[LMS] 500 Error - {error_id}',
                message=f'A 500 error occurred in the Laundry Management System.\n{error_details}',
                fail_silently=True
            )
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.error("Failed to send error notification email: %s", str(e))
    
    response = render(request, 'errors/500.html', context)
    response.status_code = 500
    return response


def csrf_failure(request, reason=""):
    """Handle CSRF verification failures."""
    context = {
        'error_code': 403,
        'error_title': 'Security Verification Failed',
        'error_reason': reason,
        'user': request.user if hasattr(request, 'user') else None,
    }
    
    # Log CSRF failures for security monitoring
    user_info = getattr(request.user, 'username', 'Anonymous') if hasattr(request, 'user') else 'Anonymous'
    logger.warning("CSRF Failure: %s - User: %s - Reason: %s", 
                  request.path, user_info, reason)
    
    response = render(request, 'errors/csrf_failure.html', context)
    response.status_code = 403
    return response


def get_client_ip(request):
    """Get the client's IP address from the request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def permission_denied_view(request, exception=None):
    """
    Custom view for permission denied scenarios.
    Can be used for more specific permission handling.
    """
    context = {
        'error_code': 403,
        'error_title': 'Permission Denied',
        'user': request.user,
        'exception': exception,
    }
    
    # Check if user is authenticated but lacks permission
    if request.user.is_authenticated:
        context['message'] = "You don't have permission to access this resource."
        context['suggestion'] = "Contact your administrator to request access."
    else:
        context['message'] = "Please log in to access this resource."
        context['suggestion'] = "Use your account credentials to sign in."
    
    logger.warning("Permission denied: %s - User: %s", 
                  request.path, 
                  request.user.username if request.user.is_authenticated else 'Anonymous')
    
    return render(request, 'errors/403.html', context, status=403)


def bad_request_view(request, exception=None):
    """
    Custom view for bad request scenarios.
    Provides more context about what went wrong.
    """
    context = {
        'error_code': 400,
        'error_title': 'Bad Request',
        'user': request.user,
        'exception': exception,
    }
    
    # Try to provide helpful context based on the request
    if request.method == 'POST':
        context['suggestion'] = "Please check your form data and try again."
    elif 'ajax' in request.META.get('HTTP_ACCEPT', '').lower():
        context['suggestion'] = "Invalid AJAX request. Please refresh the page."
    else:
        context['suggestion'] = "The request format is invalid. Please try again."
    
    logger.warning("Bad request: %s - Method: %s - User: %s", 
                  request.path, 
                  request.method, 
                  getattr(request.user, 'username', 'Anonymous'))
    
    return render(request, 'errors/400.html', context, status=400)


# Email error handling utilities
def handle_email_error(request, error_type="email_send_failure", error_message=None):
    """
    Handle email-related errors gracefully with user-friendly messages.
    """
    from django.contrib import messages
    
    if error_type == "smtp_auth_failure":
        messages.error(
            request,
            "We're currently experiencing email delivery issues. "
            "Password reset emails cannot be sent at this time. "
            "Please contact an administrator for assistance."
        )
        
        # Log for admin attention
        logger.error(
            "SMTP Authentication failure - Admin needs to check email configuration. "
            "Error: %s", error_message
        )
        
    elif error_type == "email_send_failure":
        messages.warning(
            request,
            "Your request was processed, but we couldn't send the confirmation email. "
            "If you need assistance, please contact support."
        )
        
    elif error_type == "password_reset_failure":
        messages.error(
            request,
            "Unable to send password reset email. This might be due to email service issues. "
            "Please try again later or contact an administrator."
        )
    
    return True


class EmailFailsafeMixin:
    """
    Mixin to handle email failures in views gracefully.
    """
    
    def handle_email_failure(self, error, error_type="general"):
        """Handle email failure with appropriate user feedback."""
        from django.contrib import messages
        
        request = getattr(self, 'request', None)
        
        if request:
            if error_type == "password_reset":
                messages.error(
                    request,
                    "Password reset email could not be sent due to email service issues. "
                    "Please try again later or contact support."
                )
            else:
                messages.warning(
                    request,
                    "Email notification could not be sent, but your action was completed successfully."
                )
        
        # Log the error for admin attention
        logger.error("Email failure (%s): %s", error_type, str(error))
        
        return True


def get_email_status_context():
    """
    Get email configuration status for templates.
    """
    return {
        'email_configured': bool(
            getattr(settings, 'EMAIL_HOST', '') and 
            getattr(settings, 'EMAIL_HOST_USER', '')
        ),
        'email_backend': getattr(settings, 'EMAIL_BACKEND', ''),
        'debug_mode': settings.DEBUG,
    }
