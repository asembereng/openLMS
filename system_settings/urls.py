"""
URL patterns for System Settings
"""

from .user_views import ToggleAdminView
from django.urls import include
from accounts.views import (
    UserListView as AccountsUserListView,
    UserDetailView as AccountsUserDetailView,
    UserCreateView as AccountsUserCreateView,
    UserEditView as AccountsUserEditView,
    UserDeactivateView as AccountsUserDeactivateView
)
from django.urls import path
from . import views

app_name = 'system_settings'

urlpatterns = [
    # Admin Settings Home
    path('', views.AdminSettingsHomeView.as_view(), name='admin_home'),
    
    # System Configuration
    path('system/', views.SystemConfigurationView.as_view(), name='system_config'),
    
    # Email Configuration
    path('email/', views.EmailConfigurationView.as_view(), name='email_config'),
    path('email/test/', views.test_email_config, name='test_email'),
    
    # Email Templates
    path('email-templates/', views.EmailTemplateListView.as_view(), name='email_templates'),
    path('email-templates/<int:pk>/edit/', views.EmailTemplateUpdateView.as_view(), name='email_template_edit'),
    
    # User Management - unified with accounts app
    path('users/', AccountsUserListView.as_view(template_name='system_settings/user_list.html'), name='user_management'),
    path('users/create/', AccountsUserCreateView.as_view(template_name='system_settings/user_create_modern.html'), name='user_create'),
    path('users/<int:pk>/', AccountsUserDetailView.as_view(template_name='system_settings/user_detail.html'), name='user_detail'),
    path('users/<int:pk>/edit/', AccountsUserEditView.as_view(template_name='system_settings/user_edit.html'), name='user_edit'),
    path('users/<int:pk>/deactivate/', AccountsUserDeactivateView.as_view(), name='user_deactivate'),
    path('users/<int:user_id>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),
    path('users/<int:user_id>/toggle-admin/', ToggleAdminView.as_view(), name='toggle_admin'),
    
    # Payment Methods
    path('payment-methods/', views.PaymentMethodListView.as_view(), name='payment_methods'),
    path('payment-methods/create/', views.PaymentMethodCreateView.as_view(), name='payment_method_create'),
    path('payment-methods/<int:pk>/edit/', views.PaymentMethodUpdateView.as_view(), name='payment_method_edit'),
    path('payment-methods/<int:pk>/delete/', views.PaymentMethodDeleteView.as_view(), name='payment_method_delete'),
    
    # Audit Log
    path('audit-log/', views.AuditLogView.as_view(), name='audit_log'),
]
