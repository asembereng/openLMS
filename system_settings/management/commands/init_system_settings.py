"""
Management command to initialize system settings with default values
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from system_settings.models import (
    SystemConfiguration,
    EmailConfiguration, 
    EmailTemplate,
    UserRoleConfiguration
)


class Command(BaseCommand):
    help = 'Initialize system settings with default configurations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reset existing configurations',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Initializing system settings...'))
        
        # Initialize System Configuration
        self.init_system_config(options['force'])
        
        # Initialize Email Configuration
        self.init_email_config(options['force'])
        
        # Initialize Email Templates
        self.init_email_templates(options['force'])
        
        # Initialize User Role Configurations
        self.init_user_roles(options['force'])
        
        self.stdout.write(self.style.SUCCESS('System settings initialization complete!'))

    def init_system_config(self, force=False):
        if SystemConfiguration.objects.exists() and not force:
            self.stdout.write('System configuration already exists. Use --force to reset.')
            return
        
        if force:
            SystemConfiguration.objects.all().delete()
        
        config = SystemConfiguration.objects.create(
            company_name="A&F Laundry Services",
            company_address="123 Business Street, Lagos, Nigeria",
            company_phone="+234-123-456-7890",
            company_email="info@aflaundry.com",
            tax_id="TAX-123456789",
            currency_symbol="₦",
            currency_code="NGN",
            decimal_places=2,
            timezone="Africa/Lagos",
            default_pieces_per_dozen=12,
            allow_customer_registration=True,
            require_email_verification=False
        )
        
        self.stdout.write(f'Created system configuration: {config.company_name}')

    def init_email_config(self, force=False):
        if EmailConfiguration.objects.exists() and not force:
            self.stdout.write('Email configuration already exists. Use --force to reset.')
            return
        
        if force:
            EmailConfiguration.objects.all().delete()
        
        config = EmailConfiguration.objects.create(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_username="your-email@gmail.com",
            smtp_password="your-app-password",
            use_tls=True,
            use_ssl=False,
            from_email="noreply@aflaundry.com",
            from_name="A&F Laundry Services",
            reply_to_email="support@aflaundry.com",
            test_email="admin@aflaundry.com"
        )
        
        self.stdout.write(f'Created email configuration: {config.smtp_host}:{config.smtp_port}')

    def init_email_templates(self, force=False):
        if EmailTemplate.objects.exists() and not force:
            self.stdout.write('Email templates already exist. Use --force to reset.')
            return
        
        if force:
            EmailTemplate.objects.all().delete()
        
        templates = [
            {
                'template_type': 'welcome',
                'subject': 'Welcome to {{company_name}}!',
                'html_content': '''
                <h2>Welcome to {{company_name}}!</h2>
                <p>Dear {{user_name}},</p>
                <p>Thank you for joining our laundry service! We're excited to serve you.</p>
                <p>Your account has been successfully created. You can now:</p>
                <ul>
                    <li>Place orders online</li>
                    <li>Track your laundry status</li>
                    <li>View your order history</li>
                    <li>Manage your account settings</li>
                </ul>
                <p>If you have any questions, please don't hesitate to contact us.</p>
                <p>Best regards,<br>{{company_name}} Team</p>
                ''',
                'available_variables': '{{company_name}}, {{user_name}}, {{user_email}}, {{site_url}}'
            },
            {
                'template_type': 'password_reset',
                'subject': 'Password Reset Request - {{company_name}}',
                'html_content': '''
                <h2>Password Reset Request</h2>
                <p>Dear {{user_name}},</p>
                <p>You have requested a password reset for your account at {{company_name}}.</p>
                <p>Click the link below to reset your password:</p>
                <p><a href="{{reset_link}}" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Reset Password</a></p>
                <p>If you didn't request this reset, please ignore this email.</p>
                <p>This link will expire in 24 hours for security reasons.</p>
                <p>Best regards,<br>{{company_name}} Team</p>
                ''',
                'available_variables': '{{company_name}}, {{user_name}}, {{user_email}}, {{reset_link}}'
            },
            {
                'template_type': 'order_confirmation',
                'subject': 'Order Confirmation #{{order_number}} - {{company_name}}',
                'html_content': '''
                <h2>Order Confirmation</h2>
                <p>Dear {{customer_name}},</p>
                <p>Thank you for your order! We have received your laundry order and it's being processed.</p>
                <h3>Order Details:</h3>
                <ul>
                    <li><strong>Order Number:</strong> {{order_number}}</li>
                    <li><strong>Order Date:</strong> {{order_date}}</li>
                    <li><strong>Total Amount:</strong> {{order_total}}</li>
                    <li><strong>Expected Pickup:</strong> {{pickup_date}}</li>
                </ul>
                <p>We'll notify you when your order is ready for pickup.</p>
                <p>Thank you for choosing {{company_name}}!</p>
                <p>Best regards,<br>{{company_name}} Team</p>
                ''',
                'available_variables': '{{company_name}}, {{customer_name}}, {{order_number}}, {{order_date}}, {{order_total}}, {{pickup_date}}'
            },
            {
                'template_type': 'order_ready',
                'subject': 'Your Order is Ready! #{{order_number}} - {{company_name}}',
                'html_content': '''
                <h2>Your Order is Ready for Pickup!</h2>
                <p>Dear {{customer_name}},</p>
                <p>Great news! Your laundry order #{{order_number}} is ready for pickup.</p>
                <h3>Pickup Details:</h3>
                <ul>
                    <li><strong>Order Number:</strong> {{order_number}}</li>
                    <li><strong>Total Amount:</strong> {{order_total}}</li>
                    <li><strong>Pickup Location:</strong> {{company_address}}</li>
                    <li><strong>Business Hours:</strong> Monday - Saturday, 8:00 AM - 6:00 PM</li>
                </ul>
                <p>Please bring your order receipt or provide your order number when picking up.</p>
                <p>Thank you for choosing {{company_name}}!</p>
                <p>Best regards,<br>{{company_name}} Team</p>
                ''',
                'available_variables': '{{company_name}}, {{customer_name}}, {{order_number}}, {{order_total}}, {{company_address}}'
            },
            {
                'template_type': 'user_created',
                'subject': 'New User Account Created - {{company_name}}',
                'html_content': '''
                <h2>User Account Created</h2>
                <p>Dear {{user_name}},</p>
                <p>A new user account has been created for you at {{company_name}}.</p>
                <h3>Account Details:</h3>
                <ul>
                    <li><strong>Username:</strong> {{username}}</li>
                    <li><strong>Email:</strong> {{user_email}}</li>
                    <li><strong>Role:</strong> {{user_role}}</li>
                </ul>
                <p>Please contact your administrator to receive your login credentials.</p>
                <p>You can access the system at: {{site_url}}</p>
                <p>Best regards,<br>{{company_name}} Administration</p>
                ''',
                'available_variables': '{{company_name}}, {{user_name}}, {{username}}, {{user_email}}, {{user_role}}, {{site_url}}'
            }
        ]
        
        for template_data in templates:
            template = EmailTemplate.objects.create(**template_data)
            self.stdout.write(f'Created email template: {template.get_template_type_display()}')

    def init_user_roles(self, force=False):
        if UserRoleConfiguration.objects.exists() and not force:
            self.stdout.write('User role configurations already exist. Use --force to reset.')
            return
        
        if force:
            UserRoleConfiguration.objects.all().delete()
        
        roles = [
            {
                'role_name': 'Administrator',
                'description': 'Full system access with administrative privileges',
                'can_manage_customers': True,
                'can_manage_services': True,
                'can_manage_orders': True,
                'can_manage_expenses': True,
                'can_view_reports': True,
                'can_manage_users': True,
                'can_manage_system_settings': True,
                'can_access_admin_panel': True,
                'is_active': True,
                'is_default': False
            },
            {
                'role_name': 'Regular User',
                'description': 'Standard user with access to daily operations',
                'can_manage_customers': True,
                'can_manage_services': False,
                'can_manage_orders': True,
                'can_manage_expenses': True,
                'can_view_reports': True,
                'can_manage_users': False,
                'can_manage_system_settings': False,
                'can_access_admin_panel': False,
                'is_active': True,
                'is_default': True
            },
            {
                'role_name': 'Cashier',
                'description': 'Limited access focused on order processing and customer service',
                'can_manage_customers': True,
                'can_manage_services': False,
                'can_manage_orders': True,
                'can_manage_expenses': False,
                'can_view_reports': False,
                'can_manage_users': False,
                'can_manage_system_settings': False,
                'can_access_admin_panel': False,
                'is_active': True,
                'is_default': False
            }
        ]
        
        for role_data in roles:
            role = UserRoleConfiguration.objects.create(**role_data)
            self.stdout.write(f'Created user role: {role.role_name}')
