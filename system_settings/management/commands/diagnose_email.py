"""
Management command to test and diagnose email configuration.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.mail import send_mail
from laundry_management.email_backend import SMTPConfigHelper
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test and diagnose email configuration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--to-email',
            type=str,
            help='Email address to send test email to',
            default='test@example.com'
        )
        parser.add_argument(
            '--diagnose-only',
            action='store_true',
            help='Only diagnose configuration, do not send test email'
        )
        parser.add_argument(
            '--fix-config',
            action='store_true',
            help='Suggest configuration fixes'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('=== Email Configuration Diagnostic ===')
        )
        
        # Display current configuration
        self._display_current_config()
        
        # Test SMTP connection if configured
        if self._has_smtp_config():
            self._test_smtp_connection()
        else:
            self.stdout.write(
                self.style.WARNING('SMTP not configured - using fallback backend')
            )
        
        # Send test email if requested
        if not options['diagnose_only']:
            self._send_test_email(options['to_email'])
        
        # Provide configuration suggestions
        if options['fix_config']:
            self._suggest_config_fixes()

    def _display_current_config(self):
        """Display current email configuration."""
        self.stdout.write('\n--- Current Configuration ---')
        self.stdout.write(f"Backend: {settings.EMAIL_BACKEND}")
        self.stdout.write(f"Host: {settings.EMAIL_HOST or 'Not set'}")
        self.stdout.write(f"Port: {settings.EMAIL_PORT}")
        self.stdout.write(f"Use TLS: {settings.EMAIL_USE_TLS}")
        self.stdout.write(f"Use SSL: {settings.EMAIL_USE_SSL}")
        self.stdout.write(f"Username: {settings.EMAIL_HOST_USER or 'Not set'}")
        self.stdout.write(f"Password: {'Set' if settings.EMAIL_HOST_PASSWORD else 'Not set'}")
        self.stdout.write(f"From Email: {settings.DEFAULT_FROM_EMAIL}")

    def _has_smtp_config(self):
        """Check if SMTP is properly configured."""
        return all([
            settings.EMAIL_HOST,
            settings.EMAIL_HOST_USER,
            settings.EMAIL_HOST_PASSWORD
        ]) and 'smtp' in settings.EMAIL_BACKEND.lower()

    def _test_smtp_connection(self):
        """Test SMTP connection using helper class."""
        self.stdout.write('\n--- Testing SMTP Connection ---')
        
        helper = SMTPConfigHelper()
        results = helper.test_smtp_connection(
            host=settings.EMAIL_HOST,
            port=settings.EMAIL_PORT,
            username=settings.EMAIL_HOST_USER,
            password=settings.EMAIL_HOST_PASSWORD,
            use_tls=settings.EMAIL_USE_TLS,
            use_ssl=settings.EMAIL_USE_SSL,
            timeout=getattr(settings, 'EMAIL_TIMEOUT', 30)
        )
        
        if results['success']:
            self.stdout.write(
                self.style.SUCCESS('✓ SMTP connection successful!')
            )
        else:
            self.stdout.write(
                self.style.ERROR(f'✗ SMTP connection failed: {results["error"]}')
            )
            self.stdout.write(f'Error type: {results["error_type"]}')
            
            self.stdout.write('\n--- Suggested Solutions ---')
            for suggestion in results['suggestions']:
                self.stdout.write(f"• {suggestion}")

    def _send_test_email(self, to_email):
        """Send a test email."""
        self.stdout.write('\n--- Sending Test Email ---')
        
        try:
            send_mail(
                subject='[A&F Laundry] Email Configuration Test',
                message='''This is a test email to verify email configuration.

If you receive this email, your email configuration is working correctly.

Test details:
- Sent from: A&F Laundry Management System
- Backend: {}
- Timestamp: {}

Best regards,
A&F Laundry System
'''.format(settings.EMAIL_BACKEND, 
           self._get_current_time()),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                fail_silently=False
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'✓ Test email sent successfully to {to_email}')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Failed to send test email: {e}')
            )

    def _suggest_config_fixes(self):
        """Provide configuration suggestions based on current setup."""
        self.stdout.write('\n--- Configuration Suggestions ---')
        
        helper = SMTPConfigHelper()
        common_configs = helper.get_common_smtp_configs()
        
        # Detect email provider
        if 'gmail.com' in settings.EMAIL_HOST_USER:
            provider = 'gmail'
        elif 'outlook.com' in settings.EMAIL_HOST_USER or 'hotmail.com' in settings.EMAIL_HOST_USER:
            provider = 'outlook'
        elif 'yahoo.com' in settings.EMAIL_HOST_USER:
            provider = 'yahoo'
        else:
            provider = None
        
        if provider and provider in common_configs:
            config = common_configs[provider]
            self.stdout.write(f'\nDetected {provider.title()} email. Recommended settings:')
            self.stdout.write(f"EMAIL_HOST={config['host']}")
            self.stdout.write(f"EMAIL_PORT={config['port']}")
            self.stdout.write(f"EMAIL_USE_TLS={config['use_tls']}")
            self.stdout.write(f"EMAIL_USE_SSL={config['use_ssl']}")
            
            self.stdout.write('\nRequirements:')
            for req in config['requirements']:
                self.stdout.write(f"• {req}")
        
        # General suggestions
        self.stdout.write('\n--- General Recommendations ---')
        self.stdout.write('• Use environment variables for sensitive email credentials')
        self.stdout.write('• Enable 2-factor authentication for email accounts')
        self.stdout.write('• Use App Passwords instead of account passwords')
        self.stdout.write('• Consider using dedicated email service (SendGrid, Mailgun, etc.)')
        self.stdout.write('• Test email configuration in development before production')
        
        # Environment file example
        self.stdout.write('\n--- Example .env Configuration ---')
        if provider == 'gmail':
            self.stdout.write('''# Gmail Configuration
EMAIL_BACKEND=laundry_management.email_backend.RobustEmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password_here
DEFAULT_FROM_EMAIL=your_email@gmail.com''')
        else:
            self.stdout.write('''# General SMTP Configuration
EMAIL_BACKEND=laundry_management.email_backend.RobustEmailBackend
EMAIL_HOST=your_smtp_host
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=your_email@domain.com
EMAIL_HOST_PASSWORD=your_password_or_app_password
DEFAULT_FROM_EMAIL=your_email@domain.com''')

    def _get_current_time(self):
        """Get current timestamp as string."""
        from django.utils import timezone
        return timezone.now().strftime('%Y-%m-%d %H:%M:%S %Z')
