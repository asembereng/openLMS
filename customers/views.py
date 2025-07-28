from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator

from rest_framework import generics, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema

from .models import Customer
from .forms import CustomerForm
from .serializers import CustomerSerializer, CustomerCreateSerializer, CustomerListSerializer, CustomerStatsSerializer
from loyalty.models import LoyaltyAccount


# Web Views
class CustomerListView(LoginRequiredMixin, ListView):
    """List view for customers with search and filtering"""
    model = Customer
    template_name = 'customers/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Customer.objects.select_related('created_by')
        search_query = self.request.GET.get('search', '')
        
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(phone__icontains=search_query) |
                Q(email__icontains=search_query)
            )
        
        # Filter by status
        status_filter = self.request.GET.get('status', '')
        if status_filter == 'active':
            queryset = queryset.filter(is_active=True)
        elif status_filter == 'inactive':
            queryset = queryset.filter(is_active=False)
            
        return queryset.order_by('-last_visit', 'name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        return context


class CustomerDetailView(LoginRequiredMixin, DetailView):
    """Detail view for customer with order history"""
    model = Customer
    template_name = 'customers/customer_detail.html'
    context_object_name = 'customer'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get recent orders for this customer
        # context['recent_orders'] = self.object.orders.select_related(
        #     'service', 'created_by'
        # ).order_by('-created_at')[:10]
        
        # Add loyalty points to the context
        try:
            context['loyalty_points'] = self.object.loyaltyaccount.points_balance
        except LoyaltyAccount.DoesNotExist:
            context['loyalty_points'] = 0
            
        return context


class CustomerCreateView(LoginRequiredMixin, CreateView):
    """Create view for new customers"""
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form_modern.html'
    success_url = reverse_lazy('customers:list')
    
    def get_initial(self):
        """Pre-fill name field if provided in URL"""
        initial = super().get_initial()
        name = self.request.GET.get('name', '')
        if name:
            initial['name'] = name
        return initial
    
    def get_success_url(self):
        """Handle return URL for POS integration"""
        next_url = self.request.GET.get('next')
        if next_url:
            # Add the customer ID to the return URL for POS to select the customer
            separator = '&' if '?' in next_url else '?'
            return f"{next_url}{separator}customer_created={self.object.id}"
        return super().get_success_url()
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, f'Customer "{form.instance.name}" created successfully.')
        return super().form_valid(form)


class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    """Update view for existing customers"""
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form_modern.html'
    
    def get_success_url(self):
        return reverse_lazy('customers:detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, f'Customer "{form.instance.name}" updated successfully.')
        return super().form_valid(form)


@login_required
def customer_search_ajax(request):
    """AJAX endpoint for customer search in POS"""
    search_term = request.GET.get('q', '').strip()
    
    if len(search_term) < 2:
        return JsonResponse({'customers': []})
    
    customers = Customer.objects.filter(
        Q(name__icontains=search_term) |
        Q(phone__icontains=search_term),
        is_active=True
    ).values('id', 'name', 'phone', 'email')[:10]
    
    return JsonResponse({'customers': list(customers)})


# API Views
class CustomerListCreateAPIView(generics.ListCreateAPIView):
    """API view for listing and creating customers"""
    queryset = Customer.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'phone', 'email']
    ordering_fields = ['name', 'last_visit', 'total_spent', 'created_at']
    ordering = ['-last_visit', 'name']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CustomerCreateSerializer
        return CustomerListSerializer
    
    def get_queryset(self):
        return Customer.objects.select_related('created_by')


class CustomerRetrieveUpdateAPIView(generics.RetrieveUpdateAPIView):
    """API view for retrieving and updating individual customers"""
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Customer.objects.select_related('created_by')


@extend_schema(responses=CustomerStatsSerializer)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def customer_stats_api(request):
    """API endpoint for customer statistics"""
    total_customers = Customer.objects.count()
    active_customers = Customer.objects.filter(is_active=True).count()
    new_customers_this_month = Customer.objects.filter(
        created_at__month=timezone.now().month,
        created_at__year=timezone.now().year
    ).count()
    
    return Response({
        'total_customers': total_customers,
        'active_customers': active_customers,
        'inactive_customers': total_customers - active_customers,
        'new_customers_this_month': new_customers_this_month
    })
