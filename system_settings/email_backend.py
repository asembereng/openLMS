"""
Custom Django email backend that uses EmailConfiguration from system_settings
"""
import logging
from django.core.mail.backends.smtp import EmailBackend as DjangoSMTPBackend
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from django.db import OperationalError, ProgrammingError

logger = logging.getLogger(__name__)


class SystemSettingsEmailBackend(DjangoSMTPBackend):
    """
    Email backend that uses EmailConfiguration from system_settings instead of Django settings
    """
    
    def __init__(self, host=None, port=None, username=None, password=None,
                 use_tls=None, fail_silently=False, use_ssl=None, timeout=None,
                 ssl_keyfile=None, ssl_certfile=None, **kwargs):
        
        # Try to get email configuration from database
        try:
            # Import here to avoid circular imports
            from system_settings.models import EmailConfiguration
            
            email_config = EmailConfiguration.get_config()
            
            # Use database config if available, otherwise fall back to passed parameters or Django settings
            host = host or email_config.smtp_host or getattr(settings, 'EMAIL_HOST', '')
            port = port or email_config.smtp_port or getattr(settings, 'EMAIL_PORT', 587)
            username = username or email_config.smtp_username or getattr(settings, 'EMAIL_HOST_USER', '')
            password = password or email_config.smtp_password or getattr(settings, 'EMAIL_HOST_PASSWORD', '')
            
            # Handle boolean settings with proper fallback
            if use_tls is None:
                use_tls = email_config.use_tls if email_config.use_tls is not None else getattr(settings, 'EMAIL_USE_TLS', True)
            if use_ssl is None:
                use_ssl = email_config.use_ssl if email_config.use_ssl is not None else getattr(settings, 'EMAIL_USE_SSL', False)
            
            logger.debug(
                "Using email configuration from database: %s:%s (TLS: %s, SSL: %s)",
                host, port, use_tls, use_ssl
            )
            
        except (ImportError, OperationalError, ProgrammingError) as e:
            # Database not ready or model not available (during migrations, etc.)
            logger.warning("Cannot access EmailConfiguration model (database not ready): %s", str(e))
            
            # Fall back to Django settings
            host = host or getattr(settings, 'EMAIL_HOST', '')
            port = port or getattr(settings, 'EMAIL_PORT', 587)
            username = username or getattr(settings, 'EMAIL_HOST_USER', '')
            password = password or getattr(settings, 'EMAIL_HOST_PASSWORD', '')
            use_tls = use_tls if use_tls is not None else getattr(settings, 'EMAIL_USE_TLS', True)
            use_ssl = use_ssl if use_ssl is not None else getattr(settings, 'EMAIL_USE_SSL', False)
            
            logger.debug("Using fallback email configuration from Django settings")
            
        except Exception as e:
            logger.error("Error loading email configuration from database: %s", str(e))
            
            # Fall back to Django settings or parameters
            host = host or getattr(settings, 'EMAIL_HOST', '')
            port = port or getattr(settings, 'EMAIL_PORT', 587)
            username = username or getattr(settings, 'EMAIL_HOST_USER', '')
            password = password or getattr(settings, 'EMAIL_HOST_PASSWORD', '')
            use_tls = use_tls if use_tls is not None else getattr(settings, 'EMAIL_USE_TLS', True)
            use_ssl = use_ssl if use_ssl is not None else getattr(settings, 'EMAIL_USE_SSL', False)
            
            if not all([host, username, password]):
                logger.warning("Incomplete email configuration, some emails may fail to send")
        
        # Initialize the parent SMTP backend with the configuration
        super().__init__(
            host=host,
            port=port,
            username=username,
            password=password,
            use_tls=use_tls,
            fail_silently=fail_silently,
            use_ssl=use_ssl,
            timeout=timeout,
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile,
            **kwargs
        )
    
    def send_messages(self, email_messages):
        """
        Send messages with enhanced error logging
        """
        if not email_messages:
            return 0
        
        try:
            result = super().send_messages(email_messages)
            logger.info("Successfully sent %d email(s)", result)
            
            # Update success status in database if possible
            try:
                from system_settings.models import EmailConfiguration
                from django.utils import timezone
                
                email_config = EmailConfiguration.get_config()
                email_config.last_test_success = True
                email_config.last_test_error = ''
                email_config.last_test_sent = timezone.now()
                email_config.save()
            except Exception:
                pass  # Don't fail email sending if we can't update status
            
            return result
            
        except Exception as e:
            logger.error("Failed to send emails: %s", str(e))
            
            # Try to update the EmailConfiguration with the error
            try:
                from system_settings.models import EmailConfiguration
                from django.utils import timezone
                
                email_config = EmailConfiguration.get_config()
                email_config.last_test_success = False
                email_config.last_test_error = str(e)
                email_config.last_test_sent = timezone.now()
                email_config.save()
            except Exception as update_error:
                logger.error("Failed to update email configuration with error: %s", str(update_error))
            
            if not self.fail_silently:
                raise
            return 0


class SystemSettingsEmailService:
    """
    Service class for sending emails using system settings
    """
    
    @staticmethod
    def get_email_config():
        """Get email configuration from database"""
        try:
            from system_settings.models import EmailConfiguration
            return EmailConfiguration.get_config()
        except Exception:
            raise ImproperlyConfigured("Email configuration not found in database")
    
    @staticmethod
    def get_default_from_email():
        """Get default from email from database configuration"""
        try:
            from system_settings.models import EmailConfiguration
            
            email_config = EmailConfiguration.get_config()
            if email_config.from_name:
                return f"{email_config.from_name} <{email_config.from_email}>"
            return email_config.from_email
        except Exception:
            # Fall back to Django settings
            return getattr(settings, 'DEFAULT_FROM_EMAIL', 'webmaster@localhost')
    
    @staticmethod
    def test_email_configuration():
        """
        Test email configuration by sending a test email
        """
        from django.core.mail import send_mail
        from django.utils import timezone
        
        try:
            from system_settings.models import EmailConfiguration
            
            email_config = EmailConfiguration.get_config()
            
            if not email_config.test_email:
                return {
                    'success': False,
                    'error': 'No test email address configured'
                }
            
            # Send test email
            result = send_mail(
                subject='[A&F Laundry] Email Configuration Test',
                message='This is a test email to verify your email configuration is working correctly.',
                from_email=SystemSettingsEmailService.get_default_from_email(),
                recipient_list=[email_config.test_email],
                fail_silently=False
            )
            
            # Update configuration with test results
            email_config.last_test_sent = timezone.now()
            email_config.last_test_success = result > 0
            email_config.last_test_error = ''
            email_config.save()
            
            return {
                'success': result > 0,
                'error': None if result > 0 else 'Email was not sent (unknown error)',
                'test_email': email_config.test_email
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error("Email configuration test failed: %s", error_msg)
            
            # Update configuration with error
            try:
                from system_settings.models import EmailConfiguration
                from django.utils import timezone
                
                email_config = EmailConfiguration.get_config()
                email_config.last_test_sent = timezone.now()
                email_config.last_test_success = False
                email_config.last_test_error = error_msg
                email_config.save()
            except Exception:
                pass  # Don't fail if we can't update the config
            
            return {
                'success': False,
                'error': error_msg
            }


# Dynamic override of Django's DEFAULT_FROM_EMAIL setting
def patch_default_from_email():
    """
    Dynamically override DEFAULT_FROM_EMAIL with database configuration
    """
    try:
        if not hasattr(settings, '_original_default_from_email'):
            settings._original_default_from_email = settings.DEFAULT_FROM_EMAIL
        
        # Try to get from database
        new_from_email = SystemSettingsEmailService.get_default_from_email()
        if new_from_email != settings.DEFAULT_FROM_EMAIL:
            settings.DEFAULT_FROM_EMAIL = new_from_email
            logger.debug("Updated DEFAULT_FROM_EMAIL to: %s", new_from_email)
            
    except Exception as e:
        logger.debug("Could not override DEFAULT_FROM_EMAIL with system settings: %s", str(e))

# Apply the patch when this module is imported
patch_default_from_email()
