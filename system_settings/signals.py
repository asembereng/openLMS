"""
Signal handlers for system_settings app
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.cache import cache
from django.contrib.auth.models import User
from .models import SystemConfiguration, EmailConfiguration


@receiver(post_save, sender=SystemConfiguration)
def clear_system_config_cache(sender, instance, **kwargs):
    """
    Clear cache when system configuration is updated
    to ensure all parts of the application see the changes
    """
    # Clear any cached system configuration
    cache.delete('system_config')
    
    # If we were using template fragment caching, we could also clear it here
    # But it's not being used in this application
    
    # Log the update
    import logging
    logger = logging.getLogger('django')
    logger.info(f"System configuration updated - cleared cache. Fields: {instance.currency_symbol}, {instance.currency_code}")


@receiver(post_save, sender=EmailConfiguration)
def clear_email_config_cache(sender, instance, **kwargs):
    """Clear cache when email configuration is updated"""
    cache.delete('email_config')
    
    # Log the update
    import logging
    logger = logging.getLogger('django')
    logger.info(f"Email configuration updated - cleared cache for {instance.smtp_host}")
