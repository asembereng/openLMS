"""
Admin configuration for System Settings
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    SystemConfiguration,
    EmailConfiguration,
    EmailTemplate,
    UserRoleConfiguration,
    SystemAuditLog
)


@admin.register(SystemConfiguration)
class SystemConfigurationAdmin(admin.ModelAdmin):
    """Admin for System Configuration"""
    
    fieldsets = (
        ('Company Information', {
            'fields': ('company_name', 'company_logo', 'company_address', 
                      'company_phone', 'company_email', 'tax_id')
        }),
        ('Currency & Localization', {
            'fields': ('currency_symbol', 'currency_code', 'decimal_places', 'timezone')
        }),
        ('Business Rules', {
            'fields': ('default_pieces_per_dozen',)
        }),
        ('System Features', {
            'fields': ('allow_customer_registration', 'require_email_verification')
        }),
        ('Audit Information', {
            'fields': ('created_at', 'updated_at', 'updated_by'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ('created_at', 'updated_at', 'updated_by')
    
    def has_add_permission(self, request):
        # Only allow one configuration instance
        return not SystemConfiguration.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Don't allow deletion of the configuration
        return False
    
    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(EmailConfiguration)
class EmailConfigurationAdmin(admin.ModelAdmin):
    """Admin for Email Configuration"""
    
    fieldsets = (
        ('SMTP Settings', {
            'fields': ('smtp_host', 'smtp_port', 'smtp_username', 'smtp_password',
                      'use_tls', 'use_ssl')
        }),
        ('Email Settings', {
            'fields': ('from_email', 'from_name', 'reply_to_email')
        }),
        ('Testing', {
            'fields': ('test_email', 'last_test_sent', 'last_test_success', 'last_test_error'),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('created_at', 'updated_at', 'updated_by'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ('created_at', 'updated_at', 'updated_by', 
                      'last_test_sent', 'last_test_success', 'last_test_error')
    
    def has_add_permission(self, request):
        # Only allow one configuration instance
        return not EmailConfiguration.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Don't allow deletion of the configuration
        return False
    
    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    """Admin for Email Templates"""
    
    list_display = ('template_type', 'subject', 'is_active', 'updated_at', 'updated_by')
    list_filter = ('template_type', 'is_active', 'updated_at')
    search_fields = ('template_type', 'subject', 'html_content')
    
    fieldsets = (
        ('Template Information', {
            'fields': ('template_type', 'subject', 'is_active')
        }),
        ('Email Content', {
            'fields': ('html_content', 'text_content')
        }),
        ('Help', {
            'fields': ('available_variables',),
            'description': 'Available variables that can be used in this template'
        }),
        ('Audit Information', {
            'fields': ('created_at', 'updated_at', 'updated_by'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ('created_at', 'updated_at', 'updated_by')
    
    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(UserRoleConfiguration)
class UserRoleConfigurationAdmin(admin.ModelAdmin):
    """Admin for User Role Configuration"""
    
    list_display = ('role_name', 'description', 'is_active', 'is_default')
    list_filter = ('is_active', 'is_default')
    search_fields = ('role_name', 'description')
    
    fieldsets = (
        ('Role Information', {
            'fields': ('role_name', 'description', 'is_active', 'is_default')
        }),
        ('Permissions', {
            'fields': ('can_manage_customers', 'can_manage_services', 'can_manage_orders',
                      'can_manage_expenses', 'can_view_reports', 'can_manage_users',
                      'can_manage_system_settings', 'can_access_admin_panel')
        }),
        ('Audit Information', {
            'fields': ('created_at', 'updated_at', 'updated_by'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ('created_at', 'updated_at', 'updated_by')
    
    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(SystemAuditLog)
class SystemAuditLogAdmin(admin.ModelAdmin):
    """Admin for System Audit Log"""
    
    list_display = ('user', 'action_type', 'model_name', 'object_id', 'timestamp', 'ip_address')
    list_filter = ('action_type', 'model_name', 'timestamp')
    search_fields = ('user__username', 'model_name', 'object_id', 'ip_address')
    readonly_fields = ('user', 'action_type', 'model_name', 'object_id', 'changes',
                      'ip_address', 'user_agent', 'timestamp')
    
    def has_add_permission(self, request):
        # Audit logs should only be created automatically
        return False
    
    def has_change_permission(self, request, obj=None):
        # Audit logs should not be editable
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Allow deletion for cleanup purposes
        return request.user.is_superuser
