"""
Mixins for A&F Laundry Management System
"""

from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied


class AdminRequiredMixin(UserPassesTestMixin):
    """
    Mixin that requires the user to be an admin.
    Redirects to login if not authenticated, raises PermissionDenied if not admin.
    """
    
    def test_func(self):
        return (
            self.request.user.is_authenticated and 
            hasattr(self.request.user, 'profile') and 
            self.request.user.profile.is_admin
        )
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        else:
            raise PermissionDenied("You must be an admin to access this page.")
