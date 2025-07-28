from django import template

register = template.Library()


@register.filter
def can_edit_expense(expense, user):
    """
    Template filter to check if a user can edit an expense.
    Usage: {% if expense|can_edit_expense:request.user %}
    """
    if not user or not hasattr(expense, 'can_be_edited_by'):
        return False
    return expense.can_be_edited_by(user)


@register.filter
def can_delete_expense(expense, user):
    """
    Template filter to check if a user can delete an expense.
    Usage: {% if expense|can_delete_expense:request.user %}
    """
    if not user or not hasattr(expense, 'can_be_deleted_by'):
        return False
    return expense.can_be_deleted_by(user)


@register.filter
def is_admin_user(user):
    """
    Template filter to check if a user is an admin.
    Usage: {% if request.user|is_admin_user %}
    """
    if not user or not user.is_authenticated:
        return False
    
    # Check if user is superuser
    if user.is_superuser:
        return True
    
    # Check if user has an admin profile
    if hasattr(user, 'profile'):
        return user.profile.is_admin
    
    return False


@register.simple_tag
def expense_edit_permission(expense, user):
    """
    Simple tag to check expense edit permission.
    Usage: {% expense_edit_permission expense request.user as can_edit %}
    """
    if not user or not hasattr(expense, 'can_be_edited_by'):
        return False
    return expense.can_be_edited_by(user)
