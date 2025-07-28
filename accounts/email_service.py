"""
Email service for user account notifications
"""
from django.core.mail import send_mail, get_connection
from django.template.loader import render_to_string
from django.conf import settings
from system_settings.models import EmailConfiguration, SystemConfiguration
import logging

logger = logging.getLogger(__name__)


class UserEmailService:
    """Service for sending user-related emails"""
    
    @staticmethod
    def send_welcome_email(user, password=None, created_by=None):
        """
        Send welcome email to newly created user with login credentials
        
        Args:
            user: User instance
            password: Plain text password (if available)
            created_by: User who created this account
        """
        try:
            # Get email configuration
            email_config = EmailConfiguration.get_config()
            system_config = SystemConfiguration.get_config()
            
            if not email_config.smtp_host or not user.email:
                logger.warning("Cannot send welcome email - missing email config or user email for %s", user.username)
                return False
            
            # Prepare context for email template
            context = {
                'user': user,
                'password': password,
                'created_by': created_by,
                'company_name': system_config.company_name,
                'company_phone': system_config.company_phone,
                'company_email': system_config.company_email,
                'company_address': system_config.company_address,
                'login_url': f"{settings.SITE_URL}{settings.LOGIN_URL}" if hasattr(settings, 'SITE_URL') else "your-domain.com/accounts/auth/login/",
                'support_email': email_config.reply_to_email or email_config.from_email,
            }
            
            # Render email templates
            subject = f"Welcome to {system_config.company_name} - Your Account Details"
            html_message = render_to_string('accounts/emails/welcome_email.html', context)
            plain_message = render_to_string('accounts/emails/welcome_email.txt', context)
            
            # Create custom email connection using database config
            connection = get_connection(
                host=email_config.smtp_host,
                port=email_config.smtp_port,
                username=email_config.smtp_username,
                password=email_config.smtp_password,
                use_tls=email_config.use_tls,
                use_ssl=email_config.use_ssl,
            )
            
            # Send email
            result = send_mail(
                subject=subject,
                message=plain_message,
                from_email=f"{email_config.from_name} <{email_config.from_email}>",
                recipient_list=[user.email],
                html_message=html_message,
                connection=connection,
                fail_silently=False
            )
            
            if result:
                logger.info("Welcome email sent successfully to %s", user.email)
                return True
            else:
                logger.error("Failed to send welcome email to %s - no error but result was 0", user.email)
                return False
                
        except (EmailConfiguration.DoesNotExist, SystemConfiguration.DoesNotExist) as e:
            logger.error("Email configuration error for %s: %s", user.email, str(e))
            return False
        except Exception as e:
            logger.error("Error sending welcome email to %s: %s", user.email, str(e))
            return False
    
    @staticmethod
    def send_password_reset_email(user, reset_url):
        """
        Send password reset email
        
        Args:
            user: User instance
            reset_url: Password reset URL
        """
        try:
            email_config = EmailConfiguration.get_config()
            system_config = SystemConfiguration.get_config()
            
            if not email_config.smtp_host or not user.email:
                logger.warning("Cannot send password reset email - missing config or user email for %s", user.username)
                return False
            
            context = {
                'user': user,
                'reset_url': reset_url,
                'company_name': system_config.company_name,
                'support_email': email_config.reply_to_email or email_config.from_email,
            }
            
            subject = f"Password Reset - {system_config.company_name}"
            html_message = render_to_string('accounts/emails/password_reset_email.html', context)
            plain_message = render_to_string('accounts/emails/password_reset_email.txt', context)
            
            connection = get_connection(
                host=email_config.smtp_host,
                port=email_config.smtp_port,
                username=email_config.smtp_username,
                password=email_config.smtp_password,
                use_tls=email_config.use_tls,
                use_ssl=email_config.use_ssl,
            )
            
            result = send_mail(
                subject=subject,
                message=plain_message,
                from_email=f"{email_config.from_name} <{email_config.from_email}>",
                recipient_list=[user.email],
                html_message=html_message,
                connection=connection,
                fail_silently=False
            )
            
            if result:
                logger.info("Password reset email sent successfully to %s", user.email)
                return True
            else:
                logger.error("Failed to send password reset email to %s", user.email)
                return False
                
        except Exception as e:
            logger.error("Error sending password reset email to %s: %s", user.email, str(e))
            return False
