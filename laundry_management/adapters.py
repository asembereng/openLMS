"""
Custom allauth adapter to handle email sending failures gracefully.
"""
import logging
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.models import EmailConfirmation
from allauth.account.utils import user_pk_to_url_str

logger = logging.getLogger(__name__)


class EmailFailsafeAdapter(DefaultAccountAdapter):
    """
    Custom account adapter that handles email sending failures gracefully
    and provides user-friendly feedback when email delivery fails.
    """
    
    def send_mail(self, template_prefix, email, context):
        """
        Override send_mail to handle failures gracefully and provide fallback options.
        """
        try:
            # Try sending email normally
            super().send_mail(template_prefix, email, context)
            logger.info("Email sent successfully to %s", email)
            return True
            
        except Exception as e:
            logger.error("Failed to send email to %s: %s", email, str(e))
            
            # Handle based on template type
            request = context.get('request')
            user = context.get('user')
            
            if template_prefix == 'account/email/password_reset_key':
                self._handle_password_reset_failure(request, email, context, e)
            elif template_prefix == 'account/email/email_confirmation':
                self._handle_confirmation_failure(request, user, context, e)
            else:
                self._handle_generic_failure(request, email, e)
            
            return False
    
    def _handle_password_reset_failure(self, request, email, context, error):
        """Handle password reset email failure."""
        if request:
            messages.error(
                request,
                f"Unable to send password reset email to {email}. "
                f"Please contact an administrator or try again later. "
                f"Error: Email service temporarily unavailable."
            )
            
            # Log detailed error for admins
            logger.error(
                "Password reset email failed for %s. "
                "Admin should check email configuration. Error: %s",
                email, str(error)
            )
    
    def _handle_confirmation_failure(self, request, user, context, error):
        """Handle email confirmation failure."""
        if request and user:
            # For email confirmation failures, we can be more lenient
            messages.warning(
                request,
                "Account created successfully! However, we couldn't send a confirmation email. "
                "Your account is still active. If you need to verify your email later, "
                "please contact an administrator."
            )
            
            # Optionally auto-verify the email if configured
            if getattr(settings, 'AUTO_VERIFY_EMAIL_ON_SEND_FAILURE', False):
                self._auto_verify_email(user)
                messages.info(
                    request,
                    "Your email has been automatically verified due to email service issues."
                )
    
    def _handle_generic_failure(self, request, email, error):
        """Handle other email failures."""
        if request:
            messages.warning(
                request,
                "We encountered an issue sending an email notification. "
                "Your action was completed successfully, but you may not receive an email confirmation."
            )
    
    def _auto_verify_email(self, user):
        """Automatically verify user's email address."""
        try:
            from allauth.account.models import EmailAddress
            email_address = EmailAddress.objects.get(user=user, primary=True)
            if not email_address.verified:
                email_address.verified = True
                email_address.save()
                logger.info("Auto-verified email for user %s due to send failure", user.username)
        except EmailAddress.DoesNotExist:
            logger.warning("Could not auto-verify email for user %s - EmailAddress not found", user.username)
        except Exception as e:
            logger.error("Failed to auto-verify email for user %s: %s", user.username, str(e))
    
    def get_email_confirmation_url(self, request, emailconfirmation):
        """
        Override to provide fallback URL generation.
        """
        try:
            return super().get_email_confirmation_url(request, emailconfirmation)
        except Exception as e:
            logger.error("Failed to generate confirmation URL: %s", str(e))
            # Fallback to a basic URL structure
            user_pk = user_pk_to_url_str(emailconfirmation.email_address.user)
            return request.build_absolute_uri(
                f"/accounts/auth/confirm-email/{emailconfirmation.key}/"
            )
    
    def send_confirmation_mail(self, request, emailconfirmation, signup):
        """
        Override confirmation email sending with better error handling.
        """
        try:
            super().send_confirmation_mail(request, emailconfirmation, signup)
        except Exception as e:
            logger.error("Confirmation email failed: %s", str(e))
            
            # Provide user feedback
            if request:
                if signup:
                    messages.warning(
                        request,
                        "Account created successfully! We couldn't send a confirmation email, "
                        "but your account is ready to use."
                    )
                else:
                    messages.warning(
                        request,
                        "Email confirmation couldn't be sent. Please try again later "
                        "or contact support if the issue persists."
                    )
            
            # Optionally auto-verify for new signups if configured
            if signup and getattr(settings, 'AUTO_VERIFY_EMAIL_ON_SEND_FAILURE', False):
                self._auto_verify_email(emailconfirmation.email_address.user)
    
    def is_open_for_signup(self, request):
        """
        Override to allow signup even when email service is down.
        """
        return True
    
    def clean_email(self, email):
        """
        Clean and validate email address.
        """
        email = super().clean_email(email)
        
        # Additional validation can be added here
        if email and '@' in email:
            domain = email.split('@')[1].lower()
            
            # Log common email providers for monitoring
            common_providers = ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com']
            if domain in common_providers:
                logger.debug("User signing up with %s email", domain)
        
        return email
    
    def get_from_email(self):
        """
        Get the from email address with fallback.
        """
        try:
            return super().get_from_email()
        except Exception:
            # Fallback to Django's default
            return getattr(settings, 'DEFAULT_FROM_EMAIL', 'webmaster@localhost')


# Additional utility functions for email diagnostics
def test_email_configuration():
    """
    Test email configuration and return results.
    """
    from django.core.mail import send_mail
    from django.utils import timezone
    
    results = {
        'success': False,
        'error': None,
        'backend': settings.EMAIL_BACKEND,
        'timestamp': timezone.now()
    }
    
    try:
        send_mail(
            subject='Email Configuration Test',
            message='This is a test email to verify configuration.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=['test@example.com'],
            fail_silently=False
        )
        results['success'] = True
    except Exception as e:
        results['error'] = str(e)
    
    return results


def get_email_status():
    """
    Get current email system status.
    """
    status = {
        'configured': bool(settings.EMAIL_HOST and settings.EMAIL_HOST_USER),
        'backend': settings.EMAIL_BACKEND,
        'host': settings.EMAIL_HOST,
        'port': settings.EMAIL_PORT,
        'use_tls': settings.EMAIL_USE_TLS,
        'use_ssl': settings.EMAIL_USE_SSL,
        'from_email': settings.DEFAULT_FROM_EMAIL,
    }
    
    # Don't expose sensitive information
    if settings.EMAIL_HOST_PASSWORD:
        status['password_set'] = True
    else:
        status['password_set'] = False
    
    return status
