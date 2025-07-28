from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.core.paginator import Paginator
from decimal import Decimal
from datetime import datetime, timedelta
import json

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from .models import ExpenseCategory, Expense, ExpenseAttachment, ExpenseApprovalRequest
from .serializers import (
    ExpenseCategorySerializer, ExpenseCategoryListSerializer,
    ExpenseSerializer, ExpenseListSerializer, ExpenseCreateSerializer,
    ExpenseAttachmentSerializer, ExpenseApprovalRequestSerializer,
    ExpenseStatsSerializer
)


# =============================================================================
# API Views (DRF ViewSets)
# =============================================================================

class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    """API ViewSet for expense categories"""
    queryset = ExpenseCategory.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ExpenseCategoryListSerializer
        return ExpenseCategorySerializer
    
    def get_queryset(self):
        queryset = ExpenseCategory.objects.select_related('created_by')
        
        if self.action == 'list':
            queryset = queryset.annotate(expense_count=Count('expenses'))
        
        # Filter by active status
        if self.request.query_params.get('active_only') == 'true':
            queryset = queryset.filter(is_active=True)
        
        return queryset.order_by('name')
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def expenses(self, request, pk=None):
        """Get expenses for a specific category"""
        category = self.get_object()
        expenses = category.expenses.select_related(
            'created_by', 'approved_by'
        ).order_by('-expense_date')
        
        # Apply filters
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        if date_from:
            expenses = expenses.filter(expense_date__gte=date_from)
        if date_to:
            expenses = expenses.filter(expense_date__lte=date_to)
        
        # Pagination
        page = self.paginate_queryset(expenses)
        if page is not None:
            serializer = ExpenseListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ExpenseListSerializer(expenses, many=True)
        return Response(serializer.data)


class ExpenseViewSet(viewsets.ModelViewSet):
    """API ViewSet for expenses"""
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ExpenseCreateSerializer
        elif self.action == 'list':
            return ExpenseListSerializer
        return ExpenseSerializer
    
    def get_queryset(self):
        queryset = Expense.objects.select_related(
            'category', 'created_by', 'approved_by'
        ).prefetch_related('attachments')
        
        # Filter by user role
        user = self.request.user
        if hasattr(user, 'profile') and not user.profile.is_admin:
            # Regular users can only see their own expenses
            queryset = queryset.filter(created_by=user)
        
        # Apply filters
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category_id=category)
        
        approved = self.request.query_params.get('approved')
        if approved == 'true':
            queryset = queryset.filter(is_approved=True)
        elif approved == 'false':
            queryset = queryset.filter(is_approved=False)
        
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        
        if date_from:
            queryset = queryset.filter(expense_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(expense_date__lte=date_to)
        
        return queryset.order_by('-expense_date', '-created_at')
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve an expense"""
        expense = self.get_object()
        
        # Check permissions
        if not hasattr(request.user, 'profile') or not request.user.profile.is_admin:
            return Response(
                {'error': 'Only administrators can approve expenses.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if expense.is_approved:
            return Response(
                {'error': 'Expense is already approved.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        expense.approve(request.user)
        
        return Response({
            'message': 'Expense approved successfully.',
            'expense': ExpenseSerializer(expense, context={'request': request}).data
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get expense statistics"""
        queryset = self.get_queryset()
        
        # Calculate statistics
        total_expenses = queryset.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        approved_expenses = queryset.filter(is_approved=True).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        pending_expenses = total_expenses - approved_expenses
        
        expense_count = queryset.count()
        categories_count = ExpenseCategory.objects.filter(is_active=True).count()
        
        # Top categories
        top_categories = list(
            queryset.values('category__name', 'category__color')
            .annotate(total=Sum('amount'), count=Count('id'))
            .order_by('-total')[:5]
        )
        
        # Monthly trend (last 6 months)
        monthly_trend = []
        for i in range(6):
            date = timezone.now() - timedelta(days=30 * i)
            month_total = queryset.filter(
                expense_date__year=date.year,
                expense_date__month=date.month
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            monthly_trend.append({
                'month': date.strftime('%Y-%m'),
                'month_name': date.strftime('%B %Y'),
                'total': month_total
            })
        
        monthly_trend.reverse()
        
        stats_data = {
            'total_expenses': total_expenses,
            'approved_expenses': approved_expenses,
            'pending_expenses': pending_expenses,
            'expense_count': expense_count,
            'categories_count': categories_count,
            'top_categories': top_categories,
            'monthly_trend': monthly_trend
        }
        
        serializer = ExpenseStatsSerializer(stats_data)
        return Response(serializer.data)


class ExpenseAttachmentViewSet(viewsets.ModelViewSet):
    """API ViewSet for expense attachments"""
    serializer_class = ExpenseAttachmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        return ExpenseAttachment.objects.select_related(
            'expense', 'uploaded_by'
        ).order_by('-uploaded_at')
    
    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)


class ExpenseApprovalRequestViewSet(viewsets.ModelViewSet):
    """API ViewSet for expense approval requests"""
    serializer_class = ExpenseApprovalRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = ExpenseApprovalRequest.objects.select_related(
            'expense', 'requested_by', 'responded_by'
        )
        
        # Filter by user role
        user = self.request.user
        if hasattr(user, 'profile') and not user.profile.is_admin:
            # Regular users can only see their own requests
            queryset = queryset.filter(requested_by=user)
        
        return queryset.order_by('-requested_at')
    
    def perform_create(self, serializer):
        serializer.save(requested_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def respond(self, request, pk=None):
        """Respond to an approval request"""
        approval_request = self.get_object()
        
        # Check permissions
        if not hasattr(request.user, 'profile') or not request.user.profile.is_admin:
            return Response(
                {'error': 'Only administrators can respond to approval requests.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if approval_request.status != 'pending':
            return Response(
                {'error': 'This request has already been responded to.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        response_status = request.data.get('status')
        response_message = request.data.get('message', '')
        
        if response_status not in ['approved', 'rejected']:
            return Response(
                {'error': 'Status must be either "approved" or "rejected".'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        approval_request.status = response_status
        approval_request.responded_by = request.user
        approval_request.responded_at = timezone.now()
        approval_request.response_message = response_message
        approval_request.save()
        
        # If approved, also approve the expense
        if response_status == 'approved':
            approval_request.expense.approve(request.user)
        
        return Response({
            'message': f'Request {response_status} successfully.',
            'request': ExpenseApprovalRequestSerializer(
                approval_request, 
                context={'request': request}
            ).data
        })


# =============================================================================
# Web Views (Template-based)
# =============================================================================

class ExpenseListView(LoginRequiredMixin, ListView):
    """List view for expenses"""
    model = Expense
    template_name = 'expenses/expense_list.html'
    context_object_name = 'expenses'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Expense.objects.select_related(
            'category', 'created_by', 'approved_by'
        )
        
        # Filter by user role
        if hasattr(self.request.user, 'profile') and not self.request.user.profile.is_admin:
            queryset = queryset.filter(created_by=self.request.user)
        
        # Apply filters
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category_id=category)
        
        approved = self.request.GET.get('approved')
        if approved == 'true':
            queryset = queryset.filter(is_approved=True)
        elif approved == 'false':
            queryset = queryset.filter(is_approved=False)
        
        return queryset.order_by('-expense_date', '-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = ExpenseCategory.objects.filter(is_active=True)
        context['current_category'] = self.request.GET.get('category')
        context['current_approved'] = self.request.GET.get('approved')
        return context


class ExpenseDetailView(LoginRequiredMixin, DetailView):
    """Detail view for expenses"""
    model = Expense
    template_name = 'expenses/expense_detail.html'
    context_object_name = 'expense'
    
    def get_queryset(self):
        queryset = Expense.objects.select_related(
            'category', 'created_by', 'approved_by'
        ).prefetch_related('attachments')
        
        # Filter by user role
        if hasattr(self.request.user, 'profile') and not self.request.user.profile.is_admin:
            queryset = queryset.filter(created_by=self.request.user)
        
        return queryset


class ExpenseCreateView(LoginRequiredMixin, CreateView):
    """Create view for expenses"""
    model = Expense
    template_name = 'expenses/expense_form_modern.html'
    fields = ['category', 'description', 'amount', 'expense_date', 'receipt_image', 'notes']
    success_url = reverse_lazy('expenses:list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Expense created successfully.')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = ExpenseCategory.objects.filter(is_active=True)
        return context


class ExpenseUpdateView(LoginRequiredMixin, UpdateView):
    """Update view for expenses"""
    model = Expense
    template_name = 'expenses/expense_form_modern.html'
    fields = ['category', 'description', 'amount', 'expense_date', 'receipt_image', 'notes']
    success_url = reverse_lazy('expenses:list')
    
    def get_queryset(self):
        queryset = Expense.objects.all()
        
        # Filter by user role and edit permissions
        if hasattr(self.request.user, 'profile') and not self.request.user.profile.is_admin:
            queryset = queryset.filter(
                created_by=self.request.user,
                is_approved=False
            )
        
        return queryset
    
    def form_valid(self, form):
        messages.success(self.request, 'Expense updated successfully.')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = ExpenseCategory.objects.filter(is_active=True)
        return context


class ExpenseDeleteView(LoginRequiredMixin, DeleteView):
    """Delete view for expenses"""
    model = Expense
    template_name = 'expenses/expense_confirm_delete.html'
    success_url = reverse_lazy('expenses:list')
    
    def get_queryset(self):
        # Only admins can delete expenses
        if hasattr(self.request.user, 'profile') and self.request.user.profile.is_admin:
            return Expense.objects.all()
        return Expense.objects.none()
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Expense deleted successfully.')
        return super().delete(request, *args, **kwargs)


# =============================================================================
# AJAX Views
# =============================================================================

@login_required
def expense_stats_ajax(request):
    """AJAX endpoint for expense statistics"""
    # Get base queryset
    queryset = Expense.objects.all()
    
    # Filter by user role
    if hasattr(request.user, 'profile') and not request.user.profile.is_admin:
        queryset = queryset.filter(created_by=request.user)
    
    # Apply date filters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if date_from:
        queryset = queryset.filter(expense_date__gte=date_from)
    if date_to:
        queryset = queryset.filter(expense_date__lte=date_to)
    
    # Calculate statistics
    total_expenses = queryset.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    approved_expenses = queryset.filter(is_approved=True).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    
    # Category breakdown
    category_breakdown = list(
        queryset.values('category__name', 'category__color')
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('-total')
    )
    
    return JsonResponse({
        'total_expenses': float(total_expenses),
        'approved_expenses': float(approved_expenses),
        'pending_expenses': float(total_expenses - approved_expenses),
        'expense_count': queryset.count(),
        'category_breakdown': category_breakdown
    })


@login_required
def expense_search_ajax(request):
    """AJAX endpoint for expense search"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'expenses': []})
    
    # Get base queryset
    queryset = Expense.objects.select_related('category', 'created_by')
    
    # Filter by user role
    if hasattr(request.user, 'profile') and not request.user.profile.is_admin:
        queryset = queryset.filter(created_by=request.user)
    
    # Apply search filters
    queryset = queryset.filter(
        Q(description__icontains=query) |
        Q(category__name__icontains=query) |
        Q(notes__icontains=query)
    )
    
    # Limit results
    expenses = queryset.order_by('-expense_date')[:10]
    
    # Format results
    results = []
    for expense in expenses:
        results.append({
            'id': expense.id,
            'description': expense.description,
            'amount': float(expense.amount),
            'category': expense.category.name,
            'expense_date': expense.expense_date.strftime('%Y-%m-%d'),
            'is_approved': expense.is_approved
        })
    
    return JsonResponse({'expenses': results})


@login_required
def approve_expense_ajax(request, pk):
    """AJAX endpoint for approving expenses"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    # Check permissions
    if not hasattr(request.user, 'profile') or not request.user.profile.is_admin:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        expense = get_object_or_404(Expense, pk=pk)
        
        if expense.is_approved:
            return JsonResponse({'error': 'Expense is already approved'}, status=400)
        
        expense.approve(request.user)
        
        return JsonResponse({
            'success': True,
            'message': 'Expense approved successfully',
            'expense': {
                'id': expense.id,
                'is_approved': expense.is_approved,
                'approved_by': expense.approved_by.get_full_name(),
                'approved_at': expense.approved_at.strftime('%Y-%m-%d %H:%M')
            }
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
