"""
Currency formatting template filters.
"""
from decimal import Decimal, InvalidOperation
from django import template
from django.conf import settings
from django.utils.formats import number_format
from django.utils.safestring import mark_safe

register = template.Library()

def get_currency_symbol():
    """Get currency symbol from system configuration"""
    try:
        from system_settings.models import SystemConfiguration
        config = SystemConfiguration.get_config()
        return config.currency_symbol
    except (ImportError, AttributeError, TypeError):
        # Fallback to settings if system config is not available
        return getattr(settings, 'CURRENCY_SYMBOL', '₦')

@register.filter(is_safe=True)
def currency(value, decimal_places=2):
    """
    Format a number as currency with thousand separator and fixed decimal places.
    Example: 1234.5 becomes '1,234.50'
    """
    try:
        # Convert to Decimal for accurate decimal place handling
        value = Decimal(str(value))
    except (TypeError, ValueError, InvalidOperation):
        # If conversion fails, return the original value
        return value if value else '0.00'
    
    # Format with thousand separators and fixed decimal places
    formatted = number_format(value, decimal_places, use_l10n=True, force_grouping=True)
    return formatted

@register.filter(is_safe=True)
def currency_symbol(value, decimal_places=2):
    """
    Format a number as currency with the site's currency symbol, thousand separator, 
    and fixed decimal places.
    Example: 1234.5 becomes '₦1,234.50' (if CURRENCY_SYMBOL is '₦')
    """
    formatted = currency(value, decimal_places)
    symbol = get_currency_symbol()
    return mark_safe(f"{symbol}{formatted}")

@register.filter(is_safe=True)
def currency_html(value, decimal_places=2):
    """
    Format a number as currency with the site's currency symbol, thousand separator,
    and fixed decimal places with HTML to right-align the amount.
    For use in table cells with text-align: right.
    """
    formatted = currency(value, decimal_places)
    symbol = get_currency_symbol()
    return mark_safe(f'<span class="currency-symbol">{symbol}</span><span class="currency-amount">{formatted}</span>')

@register.filter(is_safe=True)
def currency_negation(value, decimal_places=2):
    """
    Format a number as currency with the site's currency symbol, thousand separator,
    and fixed decimal places, properly handling negative values.
    Example: -1234.5 becomes '-₦1,234.50' (if CURRENCY_SYMBOL is '₦')
    """
    try:
        value = Decimal(str(value))
        is_negative = value < 0
        abs_value = abs(value)
    except (TypeError, ValueError, InvalidOperation):
        return value if value else '0.00'
    
    formatted = currency(abs_value, decimal_places)
    symbol = get_currency_symbol()
    
    if is_negative:
        return mark_safe(f"-{symbol}{formatted}")
    return mark_safe(f"{symbol}{formatted}")


@register.filter
def lookup(dictionary, key):
    """
    Template filter to look up a value in a dictionary or list of tuples.
    Usage: {{ my_dict|lookup:my_key }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key, '')
    elif isinstance(dictionary, (list, tuple)):
        # Handle list of tuples like Django choices
        for item in dictionary:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                if str(item[0]) == str(key):
                    return item[1]
    return ''
