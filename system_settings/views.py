"""
Views for System Settings Management
"""

from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, UpdateView, ListView, CreateView, DeleteView
from django.urls import reverse_lazy
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.http import JsonResponse
from django.contrib.auth.models import User, Group
from django.db import transaction

from .models import (
    SystemConfiguration,
    EmailConfiguration,
    EmailTemplate,
    UserRoleConfiguration,
    SystemAuditLog,
    PaymentMethod
)
from accounts.mixins import AdminRequiredMixin
from laundry_management.constraint_handlers import (
    handle_database_constraints, 
    check_delete_constraints,
    get_related_objects_summary
)
import json


class AdminSettingsHomeView(AdminRequiredMixin, TemplateView):
    """Main admin settings dashboard"""
    template_name = 'system_settings/admin_home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['system_config'] = SystemConfiguration.get_config()
        context['email_config'] = EmailConfiguration.get_config()
        context['total_users'] = User.objects.count()
        context['total_email_templates'] = EmailTemplate.objects.count()
        context['recent_audit_logs'] = SystemAuditLog.objects.select_related('user')[:10]
        return context


class SystemConfigurationView(AdminRequiredMixin, UpdateView):
    """System configuration settings"""
    model = SystemConfiguration
    template_name = 'system_settings/system_config.html'
    fields = [
        'company_name', 'company_logo', 'company_address', 'company_phone',
        'company_email', 'tax_id', 'currency_symbol', 'currency_code',
        'decimal_places', 'timezone', 'default_pieces_per_dozen',
        'allow_customer_registration', 'require_email_verification'
    ]
    success_url = reverse_lazy('system_settings:system_config')
    
    def get_object(self):
        return SystemConfiguration.get_config()
    
    def form_valid(self, form):
        try:
            form.instance.updated_by = self.request.user
            
            # Debug info
            print("=" * 50)
            print(f"Form is valid. Changed data: {form.changed_data}")
            print(f"Form cleaned data: {form.cleaned_data}")
            print(f"Files in request: {self.request.FILES}")
            
            # Special handling for the company logo
            if 'company_logo' in form.cleaned_data:
                if form.cleaned_data['company_logo'] is None and 'company_logo-clear' not in self.request.POST:
                    # If no new logo was uploaded and clear wasn't checked, keep the old logo
                    form.instance.company_logo = self.get_object().company_logo
                    print("Preserving existing logo as no new logo was uploaded")
                elif form.cleaned_data['company_logo']:
                    print(f"New logo detected: {form.cleaned_data['company_logo']}")
            
            # Save the form first to ensure it's in the database
            obj = form.save(commit=False)  # Get the object but don't save to DB yet
            print(f"Object before save - Company name: {obj.company_name}")
            
            # Now save it to the database
            obj.save()
            
            # Save many-to-many fields if any exist (in case we add some in the future)
            form.save_m2m()
            
            # Verify the save worked by fetching a fresh instance
            updated_config = SystemConfiguration.objects.get(pk=obj.pk)
            print(f"After save - Company name: {updated_config.company_name}")
            print(f"After save - Currency symbol: {updated_config.currency_symbol}")
            print("=" * 50)
            
            # Log the changes
            SystemAuditLog.objects.create(
                user=self.request.user,
                action_type='update',
                model_name='SystemConfiguration',
                object_id=str(obj.pk),
                changes={'updated_fields': list(form.changed_data)},
                ip_address=self.get_client_ip(),
                user_agent=self.request.META.get('HTTP_USER_AGENT', '')
            )
            
            messages.success(self.request, 'System configuration updated successfully!')
            
            # Handle AJAX requests
            if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'System configuration updated successfully!'
                })
                
            return super().form_valid(form)
            
        except Exception as e:
            print(f"Error saving system configuration: {str(e)}")
            messages.error(self.request, f'Error saving system configuration: {str(e)}')
            
            # Handle AJAX requests with error
            if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': f'Error saving system configuration: {str(e)}'
                }, status=500)
                
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        """Handle invalid form submissions"""
        print(f"Form invalid. Errors: {form.errors}")
        
        # Handle AJAX requests
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'errors': form.errors,
                'message': 'Form validation failed. Please check the form.'
            }, status=400)
            
        return super().form_invalid(form)
    
    def get_client_ip(self):
        """Get client IP address from request"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class EmailConfigurationView(AdminRequiredMixin, UpdateView):
    """Email configuration settings"""
    model = EmailConfiguration
    template_name = 'system_settings/email_config.html'
    fields = [
        'smtp_host', 'smtp_port', 'smtp_username', 'smtp_password',
        'use_tls', 'use_ssl', 'from_email', 'from_name', 'reply_to_email',
        'test_email'
    ]
    success_url = reverse_lazy('system_settings:email_config')
    
    def get_object(self):
        return EmailConfiguration.get_config()
    
    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        
        # Log the changes
        SystemAuditLog.objects.create(
            user=self.request.user,
            action_type='update',
            model_name='EmailConfiguration',
            object_id='1',
            changes={'updated_fields': list(form.changed_data)},
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
        
        messages.success(self.request, 'Email configuration updated successfully!')
        return super().form_valid(form)
    
    def get_client_ip(self):
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


@login_required
def test_email_config(request):
    """Test email configuration by sending a test email using current form values"""
    if not request.user.profile.is_admin:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    if request.method == 'POST':
        email_config = None
        try:
            # Parse JSON data from request body
            import json
            if request.content_type == 'application/json':
                form_data = json.loads(request.body)
            else:
                form_data = request.POST
            
            # Get current saved config for fallback
            saved_config = EmailConfiguration.get_config()
            
            # Use form values if provided, otherwise fall back to saved config
            test_config = {
                'smtp_host': form_data.get('smtp_host', saved_config.smtp_host),
                'smtp_port': int(form_data.get('smtp_port', saved_config.smtp_port)) if form_data.get('smtp_port') else saved_config.smtp_port,
                'smtp_username': form_data.get('smtp_username', saved_config.smtp_username),
                'smtp_password': form_data.get('smtp_password', saved_config.smtp_password),
                'from_email': form_data.get('from_email', saved_config.from_email),
                'from_name': form_data.get('from_name', saved_config.from_name),
                'reply_to_email': form_data.get('reply_to_email', saved_config.reply_to_email),
                'test_email': form_data.get('test_email', saved_config.test_email),
                'use_ssl': form_data.get('use_ssl') == 'on' if 'use_ssl' in form_data else saved_config.use_ssl,
                'use_tls': form_data.get('use_tls') == 'on' if 'use_tls' in form_data else saved_config.use_tls,
            }
            
            if not test_config['test_email']:
                return JsonResponse({
                    'success': False,
                    'error': 'Please set a test email address first'
                })
            
            # Validate required fields using current form values
            required_fields = ['smtp_host', 'smtp_port', 'smtp_username', 'smtp_password', 'from_email']
            missing_fields = []
            for field in required_fields:
                value = test_config[field]
                if not value or (isinstance(value, str) and not value.strip()):
                    missing_fields.append(field.replace('_', ' ').title())
            
            if missing_fields:
                error_msg = f'Missing required fields: {", ".join(missing_fields)}'
                saved_config.last_test_sent = timezone.now()
                saved_config.last_test_success = False
                saved_config.last_test_error = error_msg
                saved_config.save()
                return JsonResponse({
                    'success': False,
                    'error': f'Missing required email configuration: {", ".join(missing_fields)}'
                })
            
            # Check for placeholder values using current form values
            placeholder_checks = [
                ('smtp_username', 'your-email@gmail.com'),
                ('from_email', 'noreply@aflaundry.com'),
                ('test_email', 'admin@aflaundry.com'),
            ]
            
            for field, placeholder in placeholder_checks:
                value = test_config[field]
                if value == placeholder or 'example.com' in str(value):
                    error_msg = f'Please update {field.replace("_", " ")} with actual values (currently using placeholder)'
                    saved_config.last_test_sent = timezone.now()
                    saved_config.last_test_success = False
                    saved_config.last_test_error = error_msg
                    saved_config.save()
                    return JsonResponse({
                        'success': False,
                        'error': error_msg
                    })
            
            # Test SMTP connection first using current form values
            import smtplib
            import ssl
            import socket
            
            try:
                # Create SMTP connection using current form values
                if test_config['use_ssl']:
                    server = smtplib.SMTP_SSL(test_config['smtp_host'], test_config['smtp_port'])
                else:
                    server = smtplib.SMTP(test_config['smtp_host'], test_config['smtp_port'])
                
                if test_config['use_tls'] and not test_config['use_ssl']:
                    server.starttls()
                
                # Test authentication using current form values
                server.login(test_config['smtp_username'], test_config['smtp_password'])
                server.quit()
                
            except smtplib.SMTPAuthenticationError as e:
                error_msg = f'SMTP Authentication failed: {str(e)}. Please check your username and password.'
                saved_config.last_test_sent = timezone.now()
                saved_config.last_test_success = False
                saved_config.last_test_error = error_msg
                saved_config.save()
                return JsonResponse({
                    'success': False,
                    'error': error_msg
                })
            except smtplib.SMTPConnectError as e:
                error_msg = f'Cannot connect to SMTP server: {str(e)}. Please check host and port.'
                saved_config.last_test_sent = timezone.now()
                saved_config.last_test_success = False
                saved_config.last_test_error = error_msg
                saved_config.save()
                return JsonResponse({
                    'success': False,
                    'error': error_msg
                })
            except socket.timeout as e:
                error_msg = f'Connection to SMTP server timed out: {str(e)}. The server might be unavailable or blocked.'
                saved_config.last_test_sent = timezone.now()
                saved_config.last_test_success = False
                saved_config.last_test_error = error_msg
                saved_config.save()
                return JsonResponse({
                    'success': False,
                    'error': error_msg
                })
            except Exception as e:
                error_msg = f'SMTP connection test failed: {str(e)}'
                saved_config.last_test_sent = timezone.now()
                saved_config.last_test_success = False
                saved_config.last_test_error = error_msg
                saved_config.save()
                return JsonResponse({
                    'success': False,
                    'error': error_msg
                })
            
            # If SMTP connection test passed, try sending actual email using current form values
            from django.core.mail import get_connection
            from django.core.mail.message import EmailMessage
            
            connection = get_connection(
                host=test_config['smtp_host'],
                port=test_config['smtp_port'],
                username=test_config['smtp_username'],
                password=test_config['smtp_password'],
                use_tls=test_config['use_tls'],
                use_ssl=test_config['use_ssl'],
                timeout=30,  # Add timeout
            )
            
            # Test connection opening
            try:
                connection.open()
            except Exception as e:
                error_msg = f'Failed to open email connection: {str(e)}'
                saved_config.last_test_sent = timezone.now()
                saved_config.last_test_success = False
                saved_config.last_test_error = error_msg
                saved_config.save()
                return JsonResponse({
                    'success': False,
                    'error': error_msg
                })
            
            # Create and send test email using current form values
            # Prepare email headers
            headers = {}
            if test_config.get('reply_to_email'):
                headers['Reply-To'] = test_config['reply_to_email']
                
            email = EmailMessage(
                subject='Test Email from A&F Laundry System',
                body=f'This is a test email sent at {timezone.now().strftime("%Y-%m-%d %H:%M:%S")} to verify your email configuration is working correctly.\n\nIf you receive this email, your email configuration is working properly!',
                from_email=f"{test_config['from_name']} <{test_config['from_email']}>",
                to=[test_config['test_email']],
                connection=connection,
                headers=headers
            )
            
            # Actually send the email
            sent_count = email.send(fail_silently=False)
            connection.close()
            
            if sent_count != 1:
                error_msg = 'Email was not sent successfully (send count: 0)'
                saved_config.last_test_sent = timezone.now()
                saved_config.last_test_success = False
                saved_config.last_test_error = error_msg
                saved_config.save()
                return JsonResponse({
                    'success': False,
                    'error': error_msg
                })
            
            # Update test status - SUCCESS
            saved_config.last_test_sent = timezone.now()
            saved_config.last_test_success = True
            saved_config.last_test_error = ''
            saved_config.save()
            
            # Log the successful test
            SystemAuditLog.objects.create(
                user=request.user,
                action_type='email_test',
                model_name='EmailConfiguration',
                object_id='1',
                changes={'test_email': test_config['test_email'], 'success': True},
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            # Get formatted timestamp for the response
            timestamp = timezone.now().strftime('%b %d, %Y %H:%M')
            
            return JsonResponse({
                'success': True,
                'message': f'Test email sent successfully to {test_config["test_email"]}! Please check your inbox (and spam folder).',
                'timestamp': timestamp
            })
            
        except Exception as e:
            # Handle any other unexpected errors
            error_msg = f'Unexpected error: {str(e)}'
            
            # Use saved_config for error logging
            saved_config = EmailConfiguration.get_config()
            try:
                saved_config.last_test_sent = timezone.now()
                saved_config.last_test_success = False
                saved_config.last_test_error = error_msg
                saved_config.save()
                
                # Log the failed test
                test_email = form_data.get('test_email', saved_config.test_email) if 'form_data' in locals() else saved_config.test_email
                SystemAuditLog.objects.create(
                    user=request.user,
                    action_type='email_test',
                    model_name='EmailConfiguration',
                    object_id='1',
                    changes={'test_email': test_email, 'success': False, 'error': error_msg},
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
            except:
                pass  # Don't let logging errors prevent error response
            
            return JsonResponse({
                'success': False,
                'error': error_msg
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


class EmailTemplateListView(AdminRequiredMixin, ListView):
    """List all email templates"""
    model = EmailTemplate
    template_name = 'system_settings/email_templates.html'
    context_object_name = 'templates'
    ordering = ['template_type']


class EmailTemplateUpdateView(AdminRequiredMixin, UpdateView):
    """Edit email template"""
    model = EmailTemplate
    template_name = 'system_settings/email_template_edit.html'
    fields = ['subject', 'html_content', 'text_content', 'available_variables', 'is_active']
    success_url = reverse_lazy('system_settings:email_templates')
    
    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        
        # Log the changes
        SystemAuditLog.objects.create(
            user=self.request.user,
            action_type='update',
            model_name='EmailTemplate',
            object_id=str(form.instance.pk),
            changes={'updated_fields': list(form.changed_data)},
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
        
        messages.success(self.request, f'Email template "{form.instance.get_template_type_display()}" updated successfully!')
        return super().form_valid(form)
    
    def get_client_ip(self):
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class UserManagementView(AdminRequiredMixin, TemplateView):
    """User management interface"""
    template_name = 'system_settings/user_management.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['users'] = User.objects.select_related('profile').order_by('username')
        context['groups'] = Group.objects.all()
        context['roles'] = UserRoleConfiguration.objects.filter(is_active=True)
        return context


class AuditLogView(AdminRequiredMixin, ListView):
    """System audit log viewer"""
    model = SystemAuditLog
    template_name = 'system_settings/audit_log.html'
    context_object_name = 'logs'
    paginate_by = 50
    ordering = ['-timestamp']
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('user')
        
        # Filter by action type if specified
        action_type = self.request.GET.get('action_type')
        if action_type:
            queryset = queryset.filter(action_type=action_type)
        
        # Filter by user if specified
        user_id = self.request.GET.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Filter by model if specified
        model_name = self.request.GET.get('model')
        if model_name:
            queryset = queryset.filter(model_name=model_name)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action_types'] = SystemAuditLog.ACTION_TYPES
        context['users'] = User.objects.all()
        context['models'] = SystemAuditLog.objects.values_list('model_name', flat=True).distinct()
        context['current_filters'] = {
            'action_type': self.request.GET.get('action_type', ''),
            'user': self.request.GET.get('user', ''),
            'model': self.request.GET.get('model', ''),
        }
        return context


@login_required
def toggle_user_status(request, user_id):
    """Toggle user active status"""
    if not request.user.profile.is_admin:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    if request.method == 'POST':
        try:
            user = get_object_or_404(User, id=user_id)
            
            # Prevent admin from deactivating themselves
            if user == request.user:
                return JsonResponse({
                    'success': False,
                    'error': 'You cannot deactivate your own account'
                })
            
            user.is_active = not user.is_active
            user.save()
            
            # Log the change
            SystemAuditLog.objects.create(
                user=request.user,
                action_type='update',
                model_name='User',
                object_id=str(user.id),
                changes={
                    'is_active': user.is_active,
                    'username': user.username
                },
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            status = 'activated' if user.is_active else 'deactivated'
            return JsonResponse({
                'success': True,
                'message': f'User {user.username} has been {status}',
                'is_active': user.is_active
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

class PaymentMethodListView(AdminRequiredMixin, ListView):
    """List and manage payment methods"""
    model = PaymentMethod
    template_name = 'system_settings/payment_methods.html'
    context_object_name = 'payment_methods'
    ordering = ['sort_order', 'name']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class PaymentMethodCreateView(AdminRequiredMixin, CreateView):
    """Create new payment method"""
    model = PaymentMethod
    template_name = 'system_settings/payment_method_form_modern.html'
    fields = ['code', 'name', 'description', 'icon', 'is_active', 'requires_verification', 'sort_order']
    success_url = reverse_lazy('system_settings:payment_methods')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Payment method "{form.instance.name}" created successfully')
        
        # Log the action
        SystemAuditLog.objects.create(
            user=self.request.user,
            action_type='create',
            model_name='PaymentMethod',
            object_id=str(form.instance.id),
            changes={'created': form.cleaned_data}
        )
        
        return response


class PaymentMethodUpdateView(AdminRequiredMixin, UpdateView):
    """Update payment method"""
    model = PaymentMethod
    template_name = 'system_settings/payment_method_form_modern.html'
    fields = ['code', 'name', 'description', 'icon', 'is_active', 'requires_verification', 'sort_order']
    success_url = reverse_lazy('system_settings:payment_methods')
    
    def form_valid(self, form):
        old_data = {field: getattr(self.object, field) for field in form.changed_data}
        new_data = {field: form.cleaned_data[field] for field in form.changed_data}
        
        response = super().form_valid(form)
        messages.success(self.request, f'Payment method "{form.instance.name}" updated successfully')
        
        # Log the changes
        SystemAuditLog.objects.create(
            user=self.request.user,
            action_type='update',
            model_name='PaymentMethod',
            object_id=str(form.instance.id),
            changes={'old': old_data, 'new': new_data}
        )
        
        return response


class PaymentMethodDeleteView(AdminRequiredMixin, DeleteView):
    """Delete payment method with constraint checking"""
    model = PaymentMethod
    template_name = 'system_settings/payment_method_confirm_delete.html'
    success_url = reverse_lazy('system_settings:payment_methods')
    context_object_name = 'payment_method'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payment_method = self.get_object()
        
        # Check for related objects before showing delete confirmation
        can_delete, error_message, related_objects = check_delete_constraints(
            payment_method, "payment method"
        )
        
        context['can_delete'] = can_delete
        context['constraint_message'] = error_message
        context['related_objects'] = related_objects
        
        # Get detailed related objects summary
        context['related_summary'] = get_related_objects_summary(payment_method)
        
        return context
    
    @handle_database_constraints
    def delete(self, request, *args, **kwargs):
        payment_method = self.get_object()
        
        # Double-check constraints before deletion
        can_delete, error_message, related_objects = check_delete_constraints(
            payment_method, "payment method"
        )
        
        if not can_delete:
            messages.error(request, error_message)
            return redirect(self.success_url)
        
        # Log the deletion
        SystemAuditLog.objects.create(
            user=self.request.user,
            action_type='delete',
            model_name='PaymentMethod',
            object_id=str(payment_method.id),
            changes={'deleted': {'id': payment_method.id, 'name': payment_method.name}}
        )
        
        messages.success(request, f'Payment method "{payment_method.name}" deleted successfully')
        return super().delete(request, *args, **kwargs)
