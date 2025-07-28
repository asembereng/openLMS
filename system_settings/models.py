"""
System Settings Models for A&F Laundry Management System

These models store configurable system settings that can be managed 
through the admin interface instead of environment variables.
"""

from django.db import models
from django.core.validators import EmailValidator, RegexValidator
from django.contrib.auth.models import User
from django.utils import timezone
import pytz


class PaymentMethod(models.Model):
    """
    Payment method configuration for orders
    """
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique code for the payment method (e.g., cash, card, mobile_money)"
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name for the payment method"
    )
    description = models.TextField(
        blank=True,
        help_text="Optional description of the payment method"
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text="Optional icon class (e.g., fa-money-bill, fa-credit-card)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this payment method is available for selection"
    )
    requires_verification = models.BooleanField(
        default=False,
        help_text="Whether this payment method requires additional verification"
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="Display order in lists (lower numbers appear first)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Payment Method"
        verbose_name_plural = "Payment Methods"
        ordering = ["sort_order", "name"]
    
    def __str__(self):
        return self.name


class SystemConfiguration(models.Model):
    """
    Singleton model for general system configuration
    """
    # Company Information
    company_name = models.CharField(
        max_length=255, 
        default="A&F Laundry Services",
        help_text="Company name displayed throughout the system"
    )
    company_logo = models.ImageField(
        upload_to='company/',
        blank=True,
        null=True,
        help_text="Company logo (recommended: 200x60px PNG)"
    )
    company_address = models.TextField(
        blank=True,
        help_text="Full company address"
    )
    company_phone = models.CharField(
        max_length=20,
        blank=True,
        validators=[RegexValidator(
            regex=r'^\+?1?\d{9,15}$',
            message="Phone number must be in format: '+999999999'. Up to 15 digits allowed."
        )]
    )
    company_email = models.EmailField(
        blank=True,
        validators=[EmailValidator()]
    )
    tax_id = models.CharField(
        max_length=50,
        blank=True,
        help_text="Business tax identification number"
    )
    
    # Currency and Localization
    currency_symbol = models.CharField(
        max_length=5,
        default="₦",
        help_text="Currency symbol to display"
    )
    currency_code = models.CharField(
        max_length=3,
        default="NGN",
        help_text="ISO 4217 currency code"
    )
    decimal_places = models.PositiveSmallIntegerField(
        default=2,
        help_text="Number of decimal places for currency display"
    )
    
    # Timezone
    TIMEZONE_CHOICES = [(tz, tz) for tz in pytz.all_timezones]
    timezone = models.CharField(
        max_length=50,
        choices=TIMEZONE_CHOICES,
        default='Africa/Lagos',
        help_text="System timezone"
    )
    
    # Business Rules
    default_pieces_per_dozen = models.PositiveIntegerField(
        default=12,
        help_text="Default number of pieces per dozen for pricing calculations"
    )
    
    # System Features
    allow_customer_registration = models.BooleanField(
        default=True,
        help_text="Allow customers to register accounts"
    )
    require_email_verification = models.BooleanField(
        default=False,
        help_text="Require email verification for new accounts"
    )
    
    # Audit Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='system_config_updates'
    )
    
    class Meta:
        verbose_name = "System Configuration"
        verbose_name_plural = "System Configuration"
    
    def save(self, *args, **kwargs):
        # Ensure only one instance exists (singleton pattern)
        if not self.pk and SystemConfiguration.objects.exists():
            raise ValueError("Only one SystemConfiguration instance is allowed")
        super().save(*args, **kwargs)
    
    @classmethod
    def get_config(cls):
        """Get or create the system configuration"""
        # Using get() with a fresh query to prevent caching issues
        try:
            # Force a database hit by using select_for_update() which bypasses any caching
            config = cls.objects.select_for_update(nowait=True).get(pk=1)
        except cls.DoesNotExist:
            config = cls.objects.create(pk=1)  # Create with explicit primary key
        return config
    
    def __str__(self):
        return f"System Configuration - {self.company_name}"


class EmailConfiguration(models.Model):
    """
    Email server configuration
    """
    # SMTP Settings
    smtp_host = models.CharField(
        max_length=255,
        default="smtp.gmail.com",
        help_text="SMTP server hostname"
    )
    smtp_port = models.PositiveIntegerField(
        default=587,
        help_text="SMTP server port (usually 587 for TLS, 465 for SSL, 25 for plain)"
    )
    smtp_username = models.CharField(
        max_length=255,
        help_text="SMTP username (usually email address)"
    )
    smtp_password = models.CharField(
        max_length=255,
        help_text="SMTP password or app password"
    )
    use_tls = models.BooleanField(
        default=True,
        help_text="Use TLS encryption"
    )
    use_ssl = models.BooleanField(
        default=False,
        help_text="Use SSL encryption (mutually exclusive with TLS)"
    )
    
    # Email Settings
    from_email = models.EmailField(
        help_text="Default 'from' email address"
    )
    from_name = models.CharField(
        max_length=255,
        default="A&F Laundry Services",
        help_text="Default 'from' name"
    )
    reply_to_email = models.EmailField(
        blank=True,
        help_text="Reply-to email address (optional)"
    )
    
    # Test Settings
    test_email = models.EmailField(
        blank=True,
        help_text="Email address for testing email configuration"
    )
    last_test_sent = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time a test email was sent"
    )
    last_test_success = models.BooleanField(
        null=True,
        blank=True,
        help_text="Whether the last test was successful"
    )
    last_test_error = models.TextField(
        blank=True,
        help_text="Error message from last failed test"
    )
    
    # Audit Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='email_config_updates'
    )
    
    class Meta:
        verbose_name = "Email Configuration"
        verbose_name_plural = "Email Configuration"
    
    def save(self, *args, **kwargs):
        # Ensure only one instance exists (singleton pattern)
        if not self.pk and EmailConfiguration.objects.exists():
            raise ValueError("Only one EmailConfiguration instance is allowed")
        super().save(*args, **kwargs)
    
    @classmethod
    def get_config(cls):
        """Get or create the email configuration"""
        # Using get() with a fresh query to prevent caching issues
        try:
            # Force a database hit by using select_for_update() which bypasses any caching
            config = cls.objects.select_for_update(nowait=True).get(pk=1)
        except cls.DoesNotExist:
            config = cls.objects.create(pk=1)  # Create with explicit primary key
        return config
    
    def __str__(self):
        return f"Email Configuration - {self.smtp_host}:{self.smtp_port}"


class EmailTemplate(models.Model):
    """
    Customizable email templates for various system notifications
    """
    TEMPLATE_TYPES = [
        ('welcome', 'Welcome Email'),
        ('password_reset', 'Password Reset'),
        ('account_activation', 'Account Activation'),
        ('order_confirmation', 'Order Confirmation'),
        ('order_ready', 'Order Ready for Pickup'),
        ('order_delivered', 'Order Delivered'),
        ('payment_reminder', 'Payment Reminder'),
        ('user_created', 'User Account Created'),
        ('low_stock', 'Low Stock Alert'),
        ('system_maintenance', 'System Maintenance Notice'),
    ]
    
    template_type = models.CharField(
        max_length=50,
        choices=TEMPLATE_TYPES,
        unique=True,
        help_text="Type of email template"
    )
    subject = models.CharField(
        max_length=255,
        help_text="Email subject line (can include variables like {{company_name}})"
    )
    html_content = models.TextField(
        help_text="HTML email content (can include variables like {{user_name}}, {{company_name}}, etc.)"
    )
    text_content = models.TextField(
        blank=True,
        help_text="Plain text version of email content (optional)"
    )
    
    # Template Variables Help
    available_variables = models.TextField(
        blank=True,
        help_text="Available template variables for this email type"
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this template is active and should be used"
    )
    
    # Audit Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='email_template_updates'
    )
    
    class Meta:
        verbose_name = "Email Template"
        verbose_name_plural = "Email Templates"
        ordering = ['template_type']
    
    def __str__(self):
        return f"{self.get_template_type_display()}"


class UserRoleConfiguration(models.Model):
    """
    Configuration for user roles and permissions
    """
    role_name = models.CharField(
        max_length=50,
        unique=True,
        help_text="Name of the role"
    )
    description = models.TextField(
        help_text="Description of what this role can do"
    )
    
    # Permissions
    can_manage_customers = models.BooleanField(default=True)
    can_manage_services = models.BooleanField(default=False)
    can_manage_orders = models.BooleanField(default=True)
    can_manage_expenses = models.BooleanField(default=True)
    can_view_reports = models.BooleanField(default=True)
    can_manage_users = models.BooleanField(default=False)
    can_manage_system_settings = models.BooleanField(default=False)
    can_access_admin_panel = models.BooleanField(default=False)
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this role is active"
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Whether this is the default role for new users"
    )
    
    # Audit Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='role_config_updates'
    )
    
    class Meta:
        verbose_name = "User Role Configuration"
        verbose_name_plural = "User Role Configurations"
        ordering = ['role_name']
    
    def __str__(self):
        return self.role_name


class SystemAuditLog(models.Model):
    """
    Audit log for system configuration changes
    """
    ACTION_TYPES = [
        ('create', 'Created'),
        ('update', 'Updated'),
        ('delete', 'Deleted'),
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('email_test', 'Email Test'),
        ('backup', 'System Backup'),
        ('restore', 'System Restore'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs'
    )
    action_type = models.CharField(
        max_length=20,
        choices=ACTION_TYPES
    )
    model_name = models.CharField(
        max_length=100,
        help_text="Name of the model that was changed"
    )
    object_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="ID of the object that was changed"
    )
    changes = models.JSONField(
        blank=True,
        null=True,
        help_text="JSON representation of what changed"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )
    user_agent = models.TextField(
        blank=True,
        help_text="User's browser/client information"
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "System Audit Log"
        verbose_name_plural = "System Audit Logs"
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.user} - {self.action_type} - {self.model_name} at {self.timestamp}"
