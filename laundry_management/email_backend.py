"""
Custom email backend with robust error handling and fallback options.
"""
import logging
import smtplib
import socket
from django.core.mail.backends.smtp import EmailBackend as DjangoSMTPBackend
from django.core.mail.backends.console import EmailBackend as ConsoleBackend
from django.core.mail.backends.filebased import EmailBackend as FileBackend
from django.conf import settings
from django.core.mail import get_connection

logger = logging.getLogger(__name__)


class RobustEmailBackend(DjangoSMTPBackend):
    """
    Email backend with automatic fallback handling for SMTP authentication errors.
    Falls back to console or file backend when SMTP fails.
    """
    
    def __init__(self, host=None, port=None, username=None, password=None,
                 use_tls=None, fail_silently=False, use_ssl=None, timeout=None,
                 ssl_keyfile=None, ssl_certfile=None, **kwargs):
        
        super().__init__(host, port, username, password, use_tls, fail_silently,
                        use_ssl, timeout, ssl_keyfile, ssl_certfile, **kwargs)
        
        # Setup fallback backends
        self.console_backend = ConsoleBackend(fail_silently=True)
        if hasattr(settings, 'EMAIL_FILE_PATH'):
            self.file_backend = FileBackend(
                file_path=settings.EMAIL_FILE_PATH,
                fail_silently=True
            )
        else:
            self.file_backend = None
    
    def send_messages(self, email_messages):
        """
        Send messages with automatic fallback on SMTP errors.
        """
        if not email_messages:
            return 0
            
        try:
            # Try sending via SMTP first
            logger.info(f"Attempting to send {len(email_messages)} email(s) via SMTP")
            return super().send_messages(email_messages)
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP Authentication failed: {e}")
            return self._fallback_send(email_messages, "SMTP Authentication Error")
            
        except smtplib.SMTPException as e:
            logger.error(f"SMTP Error occurred: {e}")
            return self._fallback_send(email_messages, f"SMTP Error: {e}")
            
        except socket.error as e:
            logger.error(f"Network error while sending email: {e}")
            return self._fallback_send(email_messages, f"Network Error: {e}")
            
        except Exception as e:
            logger.error(f"Unexpected error while sending email: {e}")
            return self._fallback_send(email_messages, f"Unexpected Error: {e}")
    
    def _fallback_send(self, email_messages, error_reason):
        """
        Send emails using fallback backend and log the action.
        """
        logger.warning(f"SMTP failed ({error_reason}), falling back to console/file backend")
        
        # Add error notice to email subject if in debug mode
        if settings.DEBUG:
            for message in email_messages:
                original_subject = message.subject
                message.subject = f"[EMAIL FALLBACK] {original_subject}"
                
                # Add fallback notice to email body
                fallback_notice = f"\n\n--- EMAIL DELIVERY NOTICE ---\nThis email was sent via fallback method due to SMTP configuration issues.\nOriginal error: {error_reason}\n--- END NOTICE ---\n"
                
                if hasattr(message, 'body'):
                    message.body = message.body + fallback_notice
        
        # Try file backend first, then console
        if self.file_backend:
            try:
                return self.file_backend.send_messages(email_messages)
            except Exception as e:
                logger.error(f"File backend also failed: {e}")
        
        # Final fallback to console
        try:
            return self.console_backend.send_messages(email_messages)
        except Exception as e:
            logger.error(f"Console backend failed: {e}")
            if not self.fail_silently:
                raise
            return 0


class SMTPConfigHelper:
    """
    Helper class to validate and diagnose SMTP configuration issues.
    """
    
    @staticmethod
    def test_smtp_connection(host, port, username, password, use_tls=True, use_ssl=False, timeout=30):
        """
        Test SMTP connection and return detailed results.
        """
        import smtplib
        import socket
        
        results = {
            'success': False,
            'error': None,
            'error_type': None,
            'suggestions': []
        }
        
        try:
            # Create connection
            if use_ssl:
                server = smtplib.SMTP_SSL(host, port, timeout=timeout)
            else:
                server = smtplib.SMTP(host, port, timeout=timeout)
            
            # Enable debug output
            server.set_debuglevel(1)
            
            # Start TLS if required
            if use_tls and not use_ssl:
                server.starttls()
            
            # Authenticate
            if username and password:
                server.login(username, password)
            
            server.quit()
            results['success'] = True
            
        except smtplib.SMTPAuthenticationError as e:
            results['error'] = str(e)
            results['error_type'] = 'authentication'
            results['suggestions'] = [
                "Check if username and password are correct",
                "For Gmail: Enable 2-factor authentication and use App Password",
                "For Gmail: Check if 'Less secure app access' is enabled (not recommended)",
                "Verify the email account exists and is not locked",
                "Check if the email provider requires specific authentication methods"
            ]
            
        except smtplib.SMTPConnectError as e:
            results['error'] = str(e)
            results['error_type'] = 'connection'
            results['suggestions'] = [
                "Check if the SMTP server address is correct",
                "Verify the port number (usually 587 for TLS, 465 for SSL, 25 for plain)",
                "Check firewall settings",
                "Verify internet connectivity"
            ]
            
        except smtplib.SMTPServerDisconnected as e:
            results['error'] = str(e)
            results['error_type'] = 'disconnected'
            results['suggestions'] = [
                "Server may have closed the connection unexpectedly",
                "Try increasing the timeout value",
                "Check if the server is temporarily unavailable"
            ]
            
        except socket.gaierror as e:
            results['error'] = str(e)
            results['error_type'] = 'dns'
            results['suggestions'] = [
                "Check if the SMTP server hostname is correct",
                "Verify DNS resolution",
                "Check internet connectivity"
            ]
            
        except Exception as e:
            results['error'] = str(e)
            results['error_type'] = 'unknown'
            results['suggestions'] = [
                "Check all SMTP configuration parameters",
                "Consult email provider documentation",
                "Consider using a different email service"
            ]
        
        return results
    
    @staticmethod
    def get_common_smtp_configs():
        """
        Return common SMTP configurations for popular email providers.
        """
        return {
            'gmail': {
                'host': 'smtp.gmail.com',
                'port': 587,
                'use_tls': True,
                'use_ssl': False,
                'requirements': [
                    "Enable 2-factor authentication",
                    "Generate and use App Password",
                    "Use full email address as username"
                ]
            },
            'outlook': {
                'host': 'smtp-mail.outlook.com',
                'port': 587,
                'use_tls': True,
                'use_ssl': False,
                'requirements': [
                    "Use full email address as username",
                    "Use account password or app password"
                ]
            },
            'yahoo': {
                'host': 'smtp.mail.yahoo.com',
                'port': 587,
                'use_tls': True,
                'use_ssl': False,
                'requirements': [
                    "Generate and use App Password",
                    "Use full email address as username"
                ]
            },
            'sendgrid': {
                'host': 'smtp.sendgrid.net',
                'port': 587,
                'use_tls': True,
                'use_ssl': False,
                'requirements': [
                    "Use 'apikey' as username",
                    "Use SendGrid API key as password"
                ]
            }
        }
