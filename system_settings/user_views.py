from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.contrib.auth.hashers import make_password
from accounts.models import UserProfile
from accounts.mixins import AdminRequiredMixin
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import DetailView, UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from django import forms


class UserDetailView(AdminRequiredMixin, DetailView):
    """View user details (admin only)"""
    model = User
    template_name = 'system_settings/user_detail.html'
    context_object_name = 'user_obj'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()
        context['profile'] = getattr(user, 'profile', None)
        # Get recent activity for this user
        context['recent_activities'] = user.activities.all()[:10] if hasattr(user, 'activities') else []
        return context


class UserEditForm(forms.ModelForm):
    """Form for editing user details"""
    role = forms.ChoiceField(
        choices=[('normal_user', 'Regular User'), ('admin', 'Administrator')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'profile'):
            self.fields['role'].initial = self.instance.profile.role


class UserEditView(AdminRequiredMixin, UpdateView):
    """Edit user details (admin only)"""
    model = User
    form_class = UserEditForm
    template_name = 'system_settings/user_edit.html'
    context_object_name = 'user_obj'
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Update user profile role
        profile, created = UserProfile.objects.get_or_create(user=self.object)
        profile.role = form.cleaned_data['role']
        profile.save()
        
        messages.success(self.request, f'User {self.object.username} updated successfully!')
        return response
    
    def get_success_url(self):
        return reverse_lazy('system_settings:user_detail', kwargs={'pk': self.object.pk})


@method_decorator(login_required, name='dispatch')
class CreateUserView(AdminRequiredMixin, View):
    """Create user via AJAX for admin settings"""
    
    def post(self, request):
        try:
            data = request.POST
            
            # Validate required fields
            username = data.get('username', '').strip()
            email = data.get('email', '').strip()
            password1 = data.get('password1', '')
            password2 = data.get('password2', '')
            
            if not all([username, email, password1, password2]):
                return JsonResponse({
                    'success': False,
                    'error': 'All fields are required'
                })
            
            if password1 != password2:
                return JsonResponse({
                    'success': False,
                    'error': 'Passwords do not match'
                })
            
            # Check if username/email already exists
            if User.objects.filter(username=username).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'Username already exists'
                })
            
            if User.objects.filter(email=email).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'Email already exists'
                })
            
            # Create user
            user = User.objects.create(
                username=username,
                email=email,
                first_name=data.get('first_name', '').strip(),
                last_name=data.get('last_name', '').strip(),
                password=make_password(password1),
                is_active=True
            )
            
            # Create profile
            role = 'admin' if data.get('is_admin') == 'on' else 'normal_user'
            UserProfile.objects.create(
                user=user,
                role=role
            )
            
            return JsonResponse({
                'success': True,
                'message': f'User {username} created successfully!',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'full_name': user.get_full_name(),
                    'is_admin': role == 'admin'
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })


@method_decorator(login_required, name='dispatch')
class ToggleAdminView(AdminRequiredMixin, View):
    """Toggle admin status for a user"""
    
    def post(self, request, user_id):
        try:
            user = get_object_or_404(User, id=user_id)
            
            # Prevent self-demotion
            if user == request.user:
                return JsonResponse({
                    'success': False,
                    'error': 'You cannot modify your own admin privileges'
                })
            
            # Get or create profile
            profile, created = UserProfile.objects.get_or_create(user=user)
            
            # Toggle admin status
            if profile.is_admin:
                profile.role = 'normal_user'
                action = 'removed admin privileges from'
            else:
                profile.role = 'admin'
                action = 'granted admin privileges to'
            
            profile.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Successfully {action} user {user.username}',
                'is_admin': profile.is_admin
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
