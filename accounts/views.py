"""
Accounts app views
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.contenttypes.models import ContentType
from django.views.generic import (
    TemplateView, ListView, DetailView, CreateView, UpdateView, View
)
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Sum
from django.utils import timezone
from django.urls import reverse, reverse_lazy
from datetime import timedelta
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import UserProfile, UserActivity
from .serializers import UserSerializer, UserProfileSerializer
from .forms import UserProfileForm, CustomPasswordChangeForm
from .email_service import UserEmailService
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from orders.models import Order
from customers.models import Customer
from expenses.models import Expense
from .mixins import AdminRequiredMixin
from rest_framework.views import APIView


class DashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard view"""
    template_name = 'accounts/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Date ranges for stats
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Basic stats
        context['stats'] = {
            'total_customers': Customer.objects.filter(is_active=True).count(),
            'total_orders': Order.objects.count(),
            'pending_orders': Order.objects.filter(status='pending').count(),
            'ready_orders': Order.objects.filter(status='ready').count(),
            'today_orders': Order.objects.filter(created_at__date=today).count(),
            'week_revenue': Order.objects.filter(
                created_at__date__gte=week_ago,
                status='completed'
            ).aggregate(total=Sum('total_amount'))['total'] or 0,
            'month_revenue': Order.objects.filter(
                created_at__date__gte=month_ago,
                status='completed'
            ).aggregate(total=Sum('total_amount'))['total'] or 0,
        }
        
        # Recent orders
        context['recent_orders'] = Order.objects.select_related(
            'customer', 'created_by'
        ).order_by('-created_at')[:10]
        
        # Recent customers
        context['recent_customers'] = Customer.objects.select_related(
            'created_by'
        ).order_by('-created_at')[:5]
        
        return context


class LoginView(View):
    """Custom login view"""
    template_name = 'accounts/login.html'
    
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('accounts:dashboard')
        return render(request, self.template_name)
    
    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if username and password:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                # Log successful login
                UserActivity.objects.create(
                    user=user,
                    action='login',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
                return redirect('accounts:dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Please provide both username and password.')
        
        return render(request, self.template_name)


class LogoutView(LoginRequiredMixin, View):
    """Custom logout view"""
    
    def post(self, request):
        # Log logout activity
        UserActivity.objects.create(
            user=request.user,
            action='logout',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        logout(request)
        messages.success(request, 'You have been logged out successfully.')
        return redirect('accounts:login')


class ProfileView(LoginRequiredMixin, TemplateView):
    """User profile view"""
    template_name = 'accounts/profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = self.request.user.profile
        return context


class ProfileEditView(LoginRequiredMixin, UpdateView):
    """Edit user profile"""
    model = UserProfile
    template_name = 'accounts/profile_edit.html'
    fields = ['phone', 'address', 'date_of_birth', 'avatar']
    
    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile
    
    def get_success_url(self):
        messages.success(self.request, 'Profile updated successfully!')
        return reverse('accounts:profile')


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """View for updating user profile"""
    model = UserProfile
    form_class = UserProfileForm
    template_name = 'accounts/profile_update.html'
    success_url = reverse_lazy('accounts:profile')

    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Profile updated successfully!')
        return super().form_valid(form)


class PasswordChangeView(LoginRequiredMixin, TemplateView):
    """View for changing password"""
    template_name = 'accounts/password_change.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CustomPasswordChangeForm(user=self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        form = CustomPasswordChangeForm(user=request.user, data=request.POST)
        
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully!')
            return redirect('accounts:profile')
        else:
            context = self.get_context_data()
            context['form'] = form
            return self.render_to_response(context)


class UserActivityView(LoginRequiredMixin, ListView):
    """View for displaying user activity log"""
    model = UserActivity
    template_name = 'accounts/activity_log.html'
    context_object_name = 'activities'
    paginate_by = 50

    def get_queryset(self):
        return UserActivity.objects.filter(
            user=self.request.user
        ).order_by('-timestamp')


class ProfileDetailView(LoginRequiredMixin, TemplateView):
    """View for displaying user profile details"""
    template_name = 'accounts/profile_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        context['profile'] = profile
        
        # Get user statistics
        context['stats'] = {
            'orders_created': Order.objects.filter(created_by=self.request.user).count(),
            'customers_created': Customer.objects.filter(created_by=self.request.user).count(),
            'expenses_created': Expense.objects.filter(created_by=self.request.user).count(),
            'total_activity': UserActivity.objects.filter(user=self.request.user).count(),
        }
        
        # Recent activity
        context['recent_activities'] = UserActivity.objects.filter(
            user=self.request.user
        ).order_by('-timestamp')[:5]
        
        return context


class UserListView(AdminRequiredMixin, ListView):
    """List all users (admin only)"""
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    paginate_by = 20
    
    def get_queryset(self):
        return User.objects.select_related('profile').order_by('-date_joined')


class UserDetailView(AdminRequiredMixin, DetailView):
    """User detail view (admin only)"""
    model = User
    template_name = 'accounts/user_detail.html'
    context_object_name = 'user_obj'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()
        
        # User activities
        context['recent_activities'] = user.activities.order_by('-timestamp')[:20]
        
        # User stats
        context['user_stats'] = {
            'orders_created': user.orders_created.count(),
            'customers_created': user.customers_created.count(),
            'expenses_created': user.expenses_created.count(),
        }
        
        return context


class UserCreateView(AdminRequiredMixin, CreateView):
    """Create new user (admin only)"""
    model = User
    template_name = 'accounts/user_create_modern.html'
    fields = ['username', 'first_name', 'last_name', 'email', 'is_active']
    
    def form_valid(self, form):
        # Generate a random password for the new user
        password = get_random_string(12)  # 12-character random password
        
        # Set the password for the user
        form.instance.set_password(password)
        
        response = super().form_valid(form)
        
        # Create user profile
        UserProfile.objects.create(
            user=self.object,
            role=self.request.POST.get('role', 'normal_user')
        )
        
        # Send welcome email with credentials
        if self.object.email:
            email_sent = UserEmailService.send_welcome_email(
                user=self.object,
                password=password,
                created_by=self.request.user
            )
            
            if email_sent:
                messages.success(
                    self.request, 
                    f'User {self.object.username} created successfully! Welcome email sent to {self.object.email}'
                )
            else:
                messages.warning(
                    self.request,
                    f'User {self.object.username} created successfully, but failed to send welcome email. '
                    f'Please manually provide login credentials: Username: {self.object.username}, Password: {password}'
                )
        else:
            messages.success(
                self.request,
                f'User {self.object.username} created successfully! '
                f'No email provided. Manual credentials: Username: {self.object.username}, Password: {password}'
            )
        
        # Log the user creation activity
        UserActivity.objects.create(
            user=self.request.user,
            action=f'Created user: {self.object.username}',
            content_type=ContentType.objects.get_for_model(User),
            object_id=self.object.id,
            object_repr=str(self.object),
            change_message=f'Created new user with role: {self.request.POST.get("role", "normal_user")}',
            ip_address=self.get_client_ip()
        )
        
        return response
    
    def get_client_ip(self):
        """Get client IP address"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip
    
    def get_success_url(self):
        return reverse('accounts:user_detail', kwargs={'pk': self.object.pk})


class UserEditView(AdminRequiredMixin, UpdateView):
    """Edit user (admin only)"""
    model = User
    template_name = 'accounts/user_edit.html'
    fields = ['first_name', 'last_name', 'email', 'is_active']
    
    def get_success_url(self):
        messages.success(self.request, 'User updated successfully!')
        return reverse('accounts:user_detail', kwargs={'pk': self.object.pk})


class UserDeactivateView(AdminRequiredMixin, View):
    """Deactivate user (admin only)"""
    
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        user.is_active = False
        user.save()
        
        # Log the action
        UserActivity.objects.create(
            user=request.user,
            action=f'deactivated_user_{user.username}',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        messages.success(request, f'User {user.username} has been deactivated.')
        return redirect('accounts:user_detail', pk=pk)


# API ViewSets
class UserViewSet(viewsets.ModelViewSet):
    """User API ViewSet"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_permissions(self):
        """Only admins can create, update, delete users"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]


class UserProfileViewSet(viewsets.ModelViewSet):
    """User Profile API ViewSet"""
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Users can only see their own profile unless they're admin"""
        if self.request.user.is_staff:
            return UserProfile.objects.all()
        return UserProfile.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get', 'put', 'patch'])
    def me(self, request):
        """Get or update current user's profile"""
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        if request.method == 'GET':
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        else:
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RecentActivityAPI(APIView):
    """API endpoint to retrieve recent system activity"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, format=None):
        """Get recent activities across the system"""
        try:
            # Get activities from different sources and combine them
            activities = []
            
            # 1. Get recent orders and their status changes
            recent_orders = Order.objects.select_related(
                'customer', 'created_by'
            ).order_by('-updated_at')[:10]
            
            for order in recent_orders:
                icon_class = {
                    'pending': {'icon': 'info', 'icon_class': 'fa-clock'},
                    'in_progress': {'icon': 'warning', 'icon_class': 'fa-spinner'},
                    'ready': {'icon': 'info', 'icon_class': 'fa-check-circle'},
                    'completed': {'icon': 'success', 'icon_class': 'fa-check'},
                    'cancelled': {'icon': 'warning', 'icon_class': 'fa-ban'},
                }.get(order.status, {'icon': 'info', 'icon_class': 'fa-info-circle'})
                
                activities.append({
                    'icon': icon_class['icon'],
                    'icon_class': icon_class['icon_class'],
                    'title': f'Order {order.status.title()}',
                    'desc': f'Order #{order.order_number} for {order.customer.name}',
                    'time': self._format_time_ago(order.updated_at),
                    'timestamp': order.updated_at.timestamp(),
                })
            
            # 2. Get recent user activities (from audit log)
            user_activities = UserActivity.objects.select_related('user').order_by('-timestamp')[:10]
            
            for activity in user_activities:
                # Determine icon based on action type
                if 'created' in activity.action.lower():
                    icon = 'success'
                    icon_class = 'fa-plus'
                elif 'updated' in activity.action.lower() or 'edited' in activity.action.lower():
                    icon = 'info'
                    icon_class = 'fa-edit'
                elif 'deleted' in activity.action.lower():
                    icon = 'warning'
                    icon_class = 'fa-trash'
                else:
                    icon = 'info'
                    icon_class = 'fa-info-circle'
                
                activities.append({
                    'icon': icon,
                    'icon_class': icon_class,
                    'title': activity.action,
                    'desc': f'{activity.object_repr} by {activity.user.get_full_name() or activity.user.username}',
                    'time': self._format_time_ago(activity.timestamp),
                    'timestamp': activity.timestamp.timestamp(),
                })
            
            # 3. Get recent customer additions
            recent_customers = Customer.objects.select_related('created_by').order_by('-created_at')[:5]
            
            for customer in recent_customers:
                activities.append({
                    'icon': 'success',
                    'icon_class': 'fa-user-plus',
                    'title': 'New Customer Added',
                    'desc': f'{customer.name} ({customer.phone})',
                    'time': self._format_time_ago(customer.created_at),
                    'timestamp': customer.created_at.timestamp(),
                })
            
            # 4. Get recent expenses
            recent_expenses = Expense.objects.select_related('created_by').order_by('-created_at')[:5]
            
            for expense in recent_expenses:
                activities.append({
                    'icon': 'warning',
                    'icon_class': 'fa-receipt',
                    'title': 'Expense Recorded',
                    'desc': f'{expense.category}: {expense.amount} - {expense.description[:30]}',
                    'time': self._format_time_ago(expense.created_at),
                    'timestamp': expense.created_at.timestamp(),
                })
            
            # Sort activities by timestamp (most recent first) and limit to 10
            activities.sort(key=lambda x: x['timestamp'], reverse=True)
            activities = activities[:10]
            
            # Remove timestamp field as it's only used for sorting
            for activity in activities:
                del activity['timestamp']
            
            return Response(activities)
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _format_time_ago(self, timestamp):
        """Format timestamp as a human-readable 'time ago' string"""
        now = timezone.now()
        diff = now - timestamp
        
        if diff.days > 365:
            return f"{diff.days // 365} year{'s' if diff.days // 365 > 1 else ''} ago"
        if diff.days > 30:
            return f"{diff.days // 30} month{'s' if diff.days // 30 > 1 else ''} ago"
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        if diff.seconds > 3600:
            return f"{diff.seconds // 3600} hour{'s' if diff.seconds // 3600 > 1 else ''} ago"
        if diff.seconds > 60:
            return f"{diff.seconds // 60} minute{'s' if diff.seconds // 60 > 1 else ''} ago"
        return "Just now"
