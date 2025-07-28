"""
Context processors for system-wide settings
"""

from .models import SystemConfiguration, EmailConfiguration, PaymentMethod


def system_settings(request):
    """
    Add system configuration settings to template context
    Always fetches fresh data from the database to prevent stale configurations
    """
    try:
        # Use a direct query to avoid any caching issues
        from django.db import transaction
        
        # Using transaction.atomic() to ensure we get consistent data
        with transaction.atomic():
            system_config = SystemConfiguration.get_config()
            email_config = EmailConfiguration.get_config()
            
            # Get active payment methods
            payment_methods = PaymentMethod.objects.filter(is_active=True).order_by('sort_order', 'name')
        
        # Include a request-specific timestamp to prevent template caching
        from django.utils import timezone
        timestamp = timezone.now().timestamp()
        
        return {
            'system_config': system_config,
            'email_config': email_config,
            'COMPANY_NAME': system_config.company_name,
            'CURRENCY_SYMBOL': system_config.currency_symbol,
            'CURRENCY_CODE': system_config.currency_code,
            'payment_methods': payment_methods,
            '_settings_timestamp': timestamp,  # Add this to prevent caching
        }
    except Exception as e:
        import logging
        logger = logging.getLogger('django')
        logger.error(f"Error loading system settings: {str(e)}")
        
        # Return defaults if models don't exist yet (during migrations, etc.)
        return {
            'system_config': None,
            'email_config': None,
            'COMPANY_NAME': 'A&F Laundry Services',
            'CURRENCY_SYMBOL': '₦',
            'CURRENCY_CODE': 'NGN',
            '_settings_timestamp': 0,
        }
