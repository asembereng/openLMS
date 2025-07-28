"""
Management command to test email configuration and send test emails.
"""
from django.core.management.base import BaseCommand
from django.core.mail import send_mail, get_connection
from django.conf import settings
from system_settings.models import EmailConfiguration
from django.utils import timezone


class Command(BaseCommand):
    help = 'Test email configuration and send a test email'

    def add_arguments(self, parser):
        parser.add_argument(
            '--to',
            type=str,
            help='Email address to send test email to',
        )
        parser.add_argument(
            '--use-env',
            action='store_true',
            help='Use environment variables instead of database config',
        )
        parser.add_argument(
            '--check-config',
            action='store_true',
            help='Only check configuration without sending email',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔧 Email Configuration Test'))
        self.stdout.write('=' * 50)
        
        # Check current Django email backend
        self.stdout.write(f'Current EMAIL_BACKEND: {settings.EMAIL_BACKEND}')
        
        if settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
            self.stdout.write(
                self.style.WARNING(
                    '⚠️  WARNING: Using console backend - emails will be printed to console, not sent!'
                )
            )
            self.stdout.write('To enable actual email sending, update your .env file:')
            self.stdout.write('EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend')
            
            # If we're using database config, we can still send emails with custom connection
            if not options['use_env'] and not options['check_config']:
                self.stdout.write('However, we can still test email sending using database configuration...')
            elif not options['use_env'] and options['check_config']:
                self.stdout.write('Database configuration will be checked regardless...')
            elif options['check_config']:
                return
            else:
                return
        
        # Get email configuration
        if options['use_env']:
            self.stdout.write('Using environment variables...')
            config = {
                'smtp_host': getattr(settings, 'EMAIL_HOST', ''),
                'smtp_port': getattr(settings, 'EMAIL_PORT', 587),
                'smtp_username': getattr(settings, 'EMAIL_HOST_USER', ''),
                'smtp_password': getattr(settings, 'EMAIL_HOST_PASSWORD', ''),
                'use_tls': getattr(settings, 'EMAIL_USE_TLS', True),
                'use_ssl': getattr(settings, 'EMAIL_USE_SSL', False),
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
            }
        else:
            self.stdout.write('Using database configuration...')
            try:
                db_config = EmailConfiguration.get_config()
                config = {
                    'smtp_host': db_config.smtp_host,
                    'smtp_port': db_config.smtp_port,
                    'smtp_username': db_config.smtp_username,
                    'smtp_password': db_config.smtp_password,
                    'use_tls': db_config.use_tls,
                    'use_ssl': db_config.use_ssl,
                    'from_email': db_config.from_email,
                }
            except EmailConfiguration.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR('❌ Email configuration not found in database')
                )
                return
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Error loading database configuration: {e}')
                )
                return
        
        # Display configuration (hide password)
        self.stdout.write('\\nEmail Configuration:')
        self.stdout.write(f'  SMTP Host: {config["smtp_host"]}')
        self.stdout.write(f'  SMTP Port: {config["smtp_port"]}')
        self.stdout.write(f'  Username: {config["smtp_username"]}')
        self.stdout.write(f'  Password: {"*" * len(config["smtp_password"]) if config["smtp_password"] else "Not set"}')
        self.stdout.write(f'  Use TLS: {config["use_tls"]}')
        self.stdout.write(f'  Use SSL: {config["use_ssl"]}')
        self.stdout.write(f'  From Email: {config["from_email"]}')
        
        # Check for missing configuration
        required_fields = ['smtp_host', 'smtp_username', 'smtp_password', 'from_email']
        missing_fields = []
        for field in required_fields:
            if not config[field]:
                missing_fields.append(field)
        
        if missing_fields:
            self.stdout.write(
                self.style.ERROR(
                    f'❌ Missing required configuration: {", ".join(missing_fields)}'
                )
            )
            return
        
        if options['check_config']:
            self.stdout.write(self.style.SUCCESS('✅ Configuration appears valid'))
            return
        
        # Get recipient email
        to_email = options['to']
        if not to_email:
            if not options['use_env']:
                try:
                    db_config = EmailConfiguration.get_config()
                    to_email = db_config.test_email
                except Exception:
                    pass
            
            if not to_email:
                to_email = input('Enter recipient email address: ').strip()
                if not to_email:
                    self.stdout.write(self.style.ERROR('❌ No recipient email provided'))
                    return
        
        # Test SMTP connection
        self.stdout.write('\\n🔌 Testing SMTP connection...')
        try:
            import smtplib
            import socket
            
            if config['use_ssl']:
                server = smtplib.SMTP_SSL(config['smtp_host'], config['smtp_port'])
            else:
                server = smtplib.SMTP(config['smtp_host'], config['smtp_port'])
            
            if config['use_tls'] and not config['use_ssl']:
                server.starttls()
            
            server.login(config['smtp_username'], config['smtp_password'])
            server.quit()
            
            self.stdout.write(self.style.SUCCESS('✅ SMTP connection successful'))
            
        except smtplib.SMTPAuthenticationError as e:
            self.stdout.write(self.style.ERROR(f'❌ SMTP Authentication failed: {e}'))
            return
        except smtplib.SMTPConnectError as e:
            self.stdout.write(self.style.ERROR(f'❌ Cannot connect to SMTP server: {e}'))
            return
        except socket.timeout as e:
            self.stdout.write(self.style.ERROR(f'❌ SMTP connection timeout: {e}'))
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ SMTP connection failed: {e}'))
            return
        
        # Send test email
        self.stdout.write(f'\\n📧 Sending test email to {to_email}...')
        
        try:
            if options['use_env']:
                # Use Django's default email configuration
                result = send_mail(
                    subject='Test Email from A&F Laundry Management System',
                    message='This is a test email to verify email configuration.\\n\\nIf you receive this email, your email settings are working correctly!',
                    from_email=config['from_email'],
                    recipient_list=[to_email],
                    fail_silently=False
                )
            else:
                # Use custom connection with database config
                connection = get_connection(
                    host=config['smtp_host'],
                    port=config['smtp_port'],
                    username=config['smtp_username'],
                    password=config['smtp_password'],
                    use_tls=config['use_tls'],
                    use_ssl=config['use_ssl'],
                )
                
                result = send_mail(
                    subject='Test Email from A&F Laundry Management System',
                    message='This is a test email to verify email configuration.\\n\\nIf you receive this email, your email settings are working correctly!',
                    from_email=config['from_email'],
                    recipient_list=[to_email],
                    connection=connection,
                    fail_silently=False
                )
            
            if result:
                self.stdout.write(self.style.SUCCESS(f'✅ Test email sent successfully to {to_email}'))
                
                # Update database record if using database config
                if not options['use_env']:
                    try:
                        db_config = EmailConfiguration.get_config()
                        db_config.last_test_sent = timezone.now()
                        db_config.last_test_success = True
                        db_config.last_test_error = ''
                        db_config.save()
                    except Exception:
                        pass
            else:
                self.stdout.write(self.style.WARNING('⚠️  Email may not have been sent (no error but result was 0)'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Failed to send test email: {e}'))
            
            # Update database record if using database config
            if not options['use_env']:
                try:
                    db_config = EmailConfiguration.get_config()
                    db_config.last_test_sent = timezone.now()
                    db_config.last_test_success = False
                    db_config.last_test_error = str(e)
                    db_config.save()
                except Exception:
                    pass
