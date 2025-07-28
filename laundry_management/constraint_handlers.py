"""
Database constraint error handlers for the Laundry Management System.
Provides user-friendly handling of database integrity errors.
"""
import logging
from django.db import IntegrityError
from django.db.models import ProtectedError, RestrictedError
from django.contrib import messages
from django.shortcuts import redirect
from django.http import JsonResponse
from functools import wraps

logger = logging.getLogger(__name__)


class DatabaseConstraintError(Exception):
    """Custom exception for database constraint violations"""
    def __init__(self, message, error_type, related_objects=None):
        self.message = message
        self.error_type = error_type
        self.related_objects = related_objects or []
        super().__init__(self.message)


def handle_database_constraints(view_func):
    """
    Decorator to handle database constraint errors in views.
    Converts technical database errors into user-friendly messages.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except ProtectedError as e:
            return handle_protected_error(request, e)
        except RestrictedError as e:
            return handle_restricted_error(request, e)
        except IntegrityError as e:
            return handle_integrity_error(request, e)
        except DatabaseConstraintError as e:
            return handle_custom_constraint_error(request, e)
    return wrapper


def handle_protected_error(request, error):
    """Handle ProtectedError (cannot delete due to foreign key constraints)"""
    protected_objects = error.protected_objects
    
    # Get the model name and count of related objects
    if protected_objects:
        first_obj = list(protected_objects)[0]
        model_name = first_obj._meta.verbose_name
        model_name_plural = first_obj._meta.verbose_name_plural
        count = len(protected_objects)
        
        # Create user-friendly message
        if count == 1:
            message = f"Cannot delete this item because it is referenced by 1 {model_name}. Please remove or update the related {model_name} first."
        else:
            message = f"Cannot delete this item because it is referenced by {count} {model_name_plural}. Please remove or update the related {model_name_plural} first."
    else:
        message = "Cannot delete this item because it is referenced by other records in the system."
    
    # Log the error
    logger.warning(
        "Protected deletion attempted: %s - User: %s - Protected objects: %d",
        request.path,
        getattr(request.user, 'username', 'Anonymous'),
        len(protected_objects) if protected_objects else 0
    )
    
    # Handle AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': False,
            'error': 'constraint_violation',
            'message': message,
            'related_count': len(protected_objects) if protected_objects else 0
        })
    
    # Add error message and redirect
    messages.error(request, message)
    
    # Try to redirect to a sensible location
    referrer = request.META.get('HTTP_REFERER')
    if referrer:
        return redirect(referrer)
    else:
        return redirect('accounts:dashboard')


def handle_restricted_error(request, error):
    """Handle RestrictedError (similar to ProtectedError but for RESTRICT)"""
    restricted_objects = error.restricted_objects
    
    # Similar handling to ProtectedError
    if restricted_objects:
        first_obj = list(restricted_objects)[0]
        model_name_plural = first_obj._meta.verbose_name_plural
        count = len(restricted_objects)
        
        message = f"Cannot delete this item because it would affect {count} related {model_name_plural}. Please handle the dependencies first."
    else:
        message = "Cannot delete this item due to database restrictions."
    
    logger.warning(
        "Restricted deletion attempted: %s - User: %s",
        request.path,
        getattr(request.user, 'username', 'Anonymous')
    )
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': False,
            'error': 'restriction_violation',
            'message': message
        })
    
    messages.error(request, message)
    referrer = request.META.get('HTTP_REFERER')
    return redirect(referrer) if referrer else redirect('accounts:dashboard')


def handle_integrity_error(request, error):
    """Handle IntegrityError (unique constraints, null constraints, etc.)"""
    error_message = str(error).lower()
    
    # Determine the type of integrity error and create user-friendly messages
    if 'unique' in error_message or 'duplicate' in error_message:
        if 'email' in error_message:
            message = "This email address is already in use. Please choose a different one."
        elif 'username' in error_message:
            message = "This username is already taken. Please choose a different one."
        elif 'name' in error_message:
            message = "An item with this name already exists. Please choose a different name."
        elif 'code' in error_message:
            message = "This code is already in use. Please choose a different code."
        else:
            message = "This value must be unique. An item with the same information already exists."
    
    elif 'null' in error_message or 'not null' in error_message:
        message = "Required information is missing. Please fill in all required fields."
    
    elif 'foreign key' in error_message:
        message = "The selected item is invalid or no longer exists. Please refresh the page and try again."
    
    elif 'check constraint' in error_message:
        message = "The provided value is not valid for this field. Please check your input."
    
    else:
        message = "There was a problem saving your data. Please check your input and try again."
    
    # Log the error with more details
    logger.error(
        "Integrity error in %s - User: %s - Error: %s",
        request.path,
        getattr(request.user, 'username', 'Anonymous'),
        str(error)
    )
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': False,
            'error': 'integrity_violation',
            'message': message
        })
    
    messages.error(request, message)
    referrer = request.META.get('HTTP_REFERER')
    return redirect(referrer) if referrer else redirect('accounts:dashboard')


def handle_custom_constraint_error(request, error):
    """Handle custom DatabaseConstraintError exceptions"""
    logger.warning(
        "Custom constraint error in %s - User: %s - Type: %s - Message: %s",
        request.path,
        getattr(request.user, 'username', 'Anonymous'),
        error.error_type,
        error.message
    )
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': False,
            'error': error.error_type,
            'message': error.message,
            'related_objects': len(error.related_objects)
        })
    
    messages.error(request, error.message)
    referrer = request.META.get('HTTP_REFERER')
    return redirect(referrer) if referrer else redirect('accounts:dashboard')


def check_delete_constraints(obj, user_friendly_name=None):
    """
    Check if an object can be safely deleted by examining its relationships.
    Returns a tuple (can_delete: bool, message: str, related_objects: list)
    """
    if user_friendly_name is None:
        user_friendly_name = obj._meta.verbose_name
    
    related_objects = []
    
    # Get all foreign key relationships pointing to this object
    for field in obj._meta.get_fields():
        if field.one_to_many or field.one_to_one:
            if hasattr(field, 'related_model'):
                related_manager = getattr(obj, field.get_accessor_name())
                if hasattr(related_manager, 'all'):
                    related_count = related_manager.count()
                    if related_count > 0:
                        related_objects.append({
                            'model': field.related_model._meta.verbose_name_plural,
                            'count': related_count,
                            'field': field.name
                        })
    
    if related_objects:
        # Create detailed message
        if len(related_objects) == 1:
            item = related_objects[0]
            message = f"Cannot delete this {user_friendly_name} because it is used by {item['count']} {item['model']}."
        else:
            related_descriptions = [f"{item['count']} {item['model']}" for item in related_objects]
            message = f"Cannot delete this {user_friendly_name} because it is used by {', '.join(related_descriptions)}."
        
        return False, message, related_objects
    
    return True, "", []


def get_related_objects_summary(obj):
    """
    Get a summary of all objects related to the given object.
    Useful for showing users what will be affected before deletion.
    """
    related_summary = []
    
    for field in obj._meta.get_fields():
        if field.one_to_many or field.one_to_one:
            if hasattr(field, 'related_model'):
                try:
                    related_manager = getattr(obj, field.get_accessor_name())
                    if hasattr(related_manager, 'count'):
                        count = related_manager.count()
                        if count > 0:
                            related_summary.append({
                                'model_name': field.related_model._meta.verbose_name,
                                'model_name_plural': field.related_model._meta.verbose_name_plural,
                                'count': count,
                                'field_name': field.name
                            })
                except (AttributeError, ValueError, TypeError):
                    # Skip if there's an issue accessing the related manager
                    continue
    
    return related_summary
