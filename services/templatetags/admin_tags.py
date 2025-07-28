from django import template

register = template.Library()

@register.filter
def is_admin(user):
    """Check if user is admin (superuser or in Admin group)"""
    if not user.is_authenticated:
        return False
    return user.is_superuser or user.groups.filter(name='Admin').exists()

@register.simple_tag
def user_has_admin_access(user):
    """Template tag to check admin access"""
    if not user.is_authenticated:
        return False
    return user.is_superuser or user.groups.filter(name='Admin').exists()
