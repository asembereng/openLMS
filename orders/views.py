from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import timedelta
from django.views.generic import ListView, DetailView, CreateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string

from rest_framework import generics, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Order, OrderLine, OrderStatusHistory, Receipt
from .serializers import (
    OrderSerializer, OrderCreateSerializer, OrderListSerializer,
    OrderDetailSerializer, OrderUpdateStatusSerializer,
    OrderLineSerializer, ReceiptSerializer
)
from .whatsapp_service import WhatsAppService
from .pdf_service import ReceiptPDFService
from customers.models import Customer
from services.models import Service, ServiceCategory
from loyalty.services import redeem_points
from system_settings.models import SystemConfiguration


# Web Views
class OrderListView(LoginRequiredMixin, ListView):
    """List view for orders with filtering and search"""
    model = Order
    template_name = 'orders/order_list.html'
    context_object_name = 'orders'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Order.objects.select_related(
            'customer', 'created_by', 'payment_method'
        ).prefetch_related('lines__service__category')
        
        # Search
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(order_number__icontains=search_query) |
                Q(customer__name__icontains=search_query) |
                Q(customer__phone__icontains=search_query)
            )
        
        # Filter by status
        status_filter = self.request.GET.get('status', '')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by payment method
        payment_filter = self.request.GET.get('payment', '')
        if payment_filter:
            queryset = queryset.filter(payment_method__code=payment_filter)
        
        # Filter by service category
        category_filter = self.request.GET.get('category', '')
        if category_filter:
            queryset = queryset.filter(lines__service__category__id=category_filter).distinct()
        
        # Filter by date range
        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        # Filter by date presets
        date_preset = self.request.GET.get('date_preset', '')
        if date_preset:
            today = timezone.now().date()
            if date_preset == 'today':
                queryset = queryset.filter(created_at__date=today)
            elif date_preset == 'yesterday':
                yesterday = today - timedelta(days=1)
                queryset = queryset.filter(created_at__date=yesterday)
            elif date_preset == 'this_week':
                week_start = today - timedelta(days=today.weekday())
                queryset = queryset.filter(created_at__date__gte=week_start)
            elif date_preset == 'last_week':
                week_start = today - timedelta(days=today.weekday() + 7)
                week_end = week_start + timedelta(days=6)
                queryset = queryset.filter(created_at__date__gte=week_start, created_at__date__lte=week_end)
            elif date_preset == 'this_month':
                month_start = today.replace(day=1)
                queryset = queryset.filter(created_at__date__gte=month_start)
            elif date_preset == 'last_month':
                if today.month == 1:
                    last_month_start = today.replace(year=today.year - 1, month=12, day=1)
                else:
                    last_month_start = today.replace(month=today.month - 1, day=1)
                
                # Get the last day of the previous month
                if last_month_start.month == 12:
                    last_month_end = last_month_start.replace(year=last_month_start.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    last_month_end = last_month_start.replace(month=last_month_start.month + 1, day=1) - timedelta(days=1)
                
                queryset = queryset.filter(created_at__date__gte=last_month_start, created_at__date__lte=last_month_end)
            
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        from system_settings.models import PaymentMethod
        from services.models import ServiceCategory
        
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['payment_filter'] = self.request.GET.get('payment', '')
        context['category_filter'] = self.request.GET.get('category', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        context['date_preset'] = self.request.GET.get('date_preset', '')
        
        # Filter options
        context['status_choices'] = Order.STATUS_CHOICES
        context['payment_methods'] = PaymentMethod.objects.filter(is_active=True).order_by('sort_order', 'name')
        context['service_categories'] = ServiceCategory.objects.filter(is_active=True).order_by('display_order', 'name')
        
        # Date preset options
        context['date_presets'] = [
            ('', 'All Time'),
            ('today', 'Today'),
            ('yesterday', 'Yesterday'),
            ('this_week', 'This Week'),
            ('last_week', 'Last Week'),
            ('this_month', 'This Month'),
            ('last_month', 'Last Month'),
        ]
        
        # Statistics for the filtered queryset
        queryset = self.get_queryset()
        context['stats'] = {
            'total_orders': queryset.count(),
            'total_amount': queryset.aggregate(total=Sum('total_amount'))['total'] or 0,
            'pending_orders': queryset.filter(status='pending').count(),
            'in_progress_orders': queryset.filter(status='in_progress').count(),
            'ready_orders': queryset.filter(status='ready').count(),
            'completed_orders': queryset.filter(status='completed').count(),
            'cancelled_orders': queryset.filter(status='cancelled').count(),
        }
        
        # Check if any filters are active
        context['has_filters'] = any([
            self.request.GET.get('search'),
            self.request.GET.get('status'),
            self.request.GET.get('payment'),
            self.request.GET.get('category'),
            self.request.GET.get('date_from'),
            self.request.GET.get('date_to'),
            self.request.GET.get('date_preset'),
        ])
        
        return context


class OrderDetailView(LoginRequiredMixin, DetailView):
    """Detail view for individual orders"""
    model = Order
    template_name = 'orders/order_detail.html'
    context_object_name = 'order'
    
    def get_queryset(self):
        return Order.objects.select_related(
            'customer', 'created_by'
        ).prefetch_related(
            'lines__service__category',
            'status_history__changed_by'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_edit'] = self.object.can_be_cancelled
        context['loyalty_discount'] = self.object.loyalty_discount_amount
        context['redeemed_points'] = self.object.redeemed_points
        return context


class POSView(LoginRequiredMixin, CreateView):
    """Point of Sale view with mobile workflow for creating new orders"""
    model = Order
    template_name = 'orders/mobile_workflow.html'  # Updated to use mobile workflow
    fields = []  # We'll handle form creation manually
    
    def get_context_data(self, **kwargs):
        from system_settings.models import PaymentMethod
        
        context = super().get_context_data(**kwargs)
        context['customers'] = Customer.objects.filter(is_active=True)[:10]  # Recent customers
        context['services'] = Service.objects.select_related('category').filter(is_active=True)
        context['payment_methods'] = PaymentMethod.objects.filter(is_active=True).order_by('sort_order', 'name')
        return context


class DesktopPOSView(LoginRequiredMixin, CreateView):
    """Desktop-only Point of Sale view for creating new orders"""
    model = Order
    template_name = 'orders/pos.html'  # Original POS template
    fields = []  # We'll handle form creation manually
    
    def get_context_data(self, **kwargs):
        from system_settings.models import PaymentMethod
        from services.models import Service, ServiceCategory
        
        context = super().get_context_data(**kwargs)
        context['customers'] = Customer.objects.filter(is_active=True).order_by('-created_at')[:20]
        
        # Group services by category for better display
        services_by_category = {}
        categories = ServiceCategory.objects.filter(is_active=True).order_by('display_order', 'name')

        for category in categories:
            services = Service.objects.filter(category=category, is_active=True)
            if services.exists():
                services_by_category[category] = services
        
        context['services_by_category'] = services_by_category
        context['payment_methods'] = PaymentMethod.objects.filter(is_active=True).order_by('sort_order', 'name')
        
        # Add customer's loyalty points to context if a customer is selected
        customer_id = self.request.GET.get('customer_id')
        if customer_id:
            try:
                customer = Customer.objects.get(id=customer_id)
                context['loyalty_points'] = customer.loyalty_points
            except Customer.DoesNotExist:
                context['loyalty_points'] = 0
        
        return context

    def post(self, request, *args, **kwargs):
        """Handle order creation with loyalty point redemption."""
        from .forms import OrderForm  # Assuming you have a form for order creation

        form = OrderForm(request.POST)
        if not form.is_valid():
            return self.form_invalid(form)

        order = form.save(commit=False)
        order.created_by = request.user

        # Handle loyalty point redemption
        points_to_redeem = request.POST.get('redeem_points', 0)
        if points_to_redeem and int(points_to_redeem) > 0:
            try:
                points_to_redeem = int(points_to_redeem)
                customer = order.customer
                
                # The redeem_points function will handle validation and exceptions
                success, message, discount_amount, redeemed_points = redeem_points(
                    customer_id=customer.id,
                    points_to_redeem=points_to_redeem,
                    order=order  # Pass the unsaved order instance
                )

                if success:
                    order.loyalty_discount_amount = discount_amount
                    order.redeemed_points = redeemed_points
                    messages.success(request, message)
                else:
                    messages.error(request, message)
                    return self.form_invalid(form)

            except ValueError:
                messages.error(request, "Invalid number of points entered.")
                return self.form_invalid(form)
            except Exception as e:
                messages.error(request, f"An error occurred during redemption: {str(e)}")
                return self.form_invalid(form)
        
        # Save the order first to get a PK for order lines
        order.save()

        # Create OrderLine items from the POST data
        # This assumes the frontend sends data in a format like 'lines[0][service_id]', 'lines[0][pieces]'
        lines_data = []
        for key, value in request.POST.items():
            if key.startswith('lines['):
                # Extract index and field name (e.g., 0, service_id)
                parts = key.replace('lines[', '').replace(']', '').split('[')
                index = int(parts[0])
                field = parts[1]
                
                # Ensure we have a placeholder for this line
                while len(lines_data) <= index:
                    lines_data.append({})
                
                lines_data[index][field] = value

        for line_data in lines_data:
            if line_data.get('service_id') and line_data.get('pieces'):
                OrderLine.objects.create(
                    order=order,
                    service_id=int(line_data['service_id']),
                    pieces=int(line_data['pieces'])
                )

        # Recalculate totals now that lines are saved
        order.calculate_totals()  # This will now include subtotal from lines
        order.save() # Save again to store the correct totals

        messages.success(request, "Order created successfully.")
        return redirect(reverse_lazy('orders:detail', kwargs={'pk': order.pk}))


@login_required
def update_order_status(request, pk):
    """Update order status and handle both AJAX and regular form submissions"""
    if request.method != 'POST':
        # Redirect to order detail page if accessed via GET
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False, 
                'error': 'Method not allowed. Use POST to update status.'
            }, status=405)
        return redirect('orders:detail', pk=pk)
    
    try:
        order = get_object_or_404(Order, pk=pk)
        new_status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        
        status_choices = dict(Order.STATUS_CHOICES)
        if not new_status:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Status value is required'
                }, status=400)
            messages.error(request, 'Status value is required')
            return redirect('orders:detail', pk=pk)
            
        if new_status not in status_choices:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': f'Invalid status value: {new_status}'
                }, status=400)
            messages.error(request, 'Invalid status value')
            return redirect('orders:detail', pk=pk)
            
        # Validate status transition logic
        old_status = order.status
        valid_transitions = {
            'pending': ['in_progress', 'cancelled'],
            'in_progress': ['ready', 'cancelled'],
            'ready': ['completed', 'delivered', 'cancelled'],
            'completed': ['delivered'],
            'delivered': [],  # Terminal state
            'cancelled': [],  # Terminal state
        }
        
        if new_status not in valid_transitions.get(old_status, []):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': f'Invalid status transition from {old_status} to {new_status}'
                }, status=400)
            messages.error(request, f'Cannot change status from {old_status} to {new_status}')
            return redirect('orders:detail', pk=pk)
        
        old_status = order.status
        order.status = new_status
        order.save()
        
        # Create status history
        history_entry = OrderStatusHistory.objects.create(
            order=order,
            old_status=old_status,
            new_status=new_status,
            changed_by=request.user,
            notes=notes
        )
        
        # Update timestamps
        if new_status == 'completed' and not order.completed_at:
            order.completed_at = timezone.now()
            order.save(update_fields=['completed_at'])
        elif new_status == 'delivered' and not order.delivered_at:
            order.delivered_at = timezone.now()
            order.save(update_fields=['delivered_at'])
        
        # Add a user-friendly status message
        status_display = status_choices[new_status]
        messages.success(request, f'Order status updated to {status_display}')
        
        # Return appropriate response based on request type
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # AJAX request
            return JsonResponse({
                'success': True,
                'message': status_display,
                'new_status': new_status,
                'new_status_display': status_display,
                'order_id': order.pk,
                'status_history_added': True,
                'history_id': history_entry.id
            })
        else:
            # Regular form submission - redirect back to order detail
            return redirect('orders:detail', pk=pk)
            
    except Exception as e:
        # Handle any unexpected errors
        error_message = str(e)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': f'Error updating status: {error_message}'
            }, status=500)
        
        messages.error(request, f'Error updating status: {error_message}')
        return redirect('orders:detail', pk=pk)


@login_required
def generate_receipt(request, pk):
    """Generate and return receipt for order"""
    order = get_object_or_404(Order, pk=pk)
    
    # Check if receipt already exists
    receipt, created = Receipt.objects.get_or_create(
        order=order,
        defaults={
            'receipt_number': f'REC{order.order_number[3:]}',
            'generated_by': request.user,
            'content': {
                'order_number': order.order_number,
                'customer': order.customer.name,
                'total_amount': float(order.total_amount),
                'payment_method': order.payment_method.name,
                'generated_at': timezone.now().isoformat()
            }
        }
    )
    
    # Get system configuration for template context
    from system_settings.models import SystemConfiguration
    system_config = SystemConfiguration.get_config()
    
    # Render receipt template
    receipt_html = render_to_string('orders/receipt.html', {
        'order': order,
        'receipt': receipt,
        'lines': order.lines.select_related('service__category'),
        'system_config': system_config,
    })
    
    return HttpResponse(receipt_html)


@login_required
def generate_receipt_pdf(request, pk):
    """Generate PDF receipt for order"""
    order = get_object_or_404(Order, pk=pk)
    
    # Check if receipt already exists
    receipt, created = Receipt.objects.get_or_create(
        order=order,
        defaults={
            'receipt_number': f'REC{order.order_number[3:]}',
            'generated_by': request.user,
            'content': {
                'order_number': order.order_number,
                'customer': order.customer.name,
                'total_amount': float(order.total_amount),
                'payment_method': order.payment_method.name,
                'generated_at': timezone.now().isoformat()
            }
        }
    )
    
    # Generate PDF
    pdf_service = ReceiptPDFService()
    download = request.GET.get('download', 'false').lower() == 'true'
    
    return pdf_service.generate_receipt_pdf(order, receipt, download=download)


@login_required
def validate_whatsapp_number(request, pk):
    """Validate customer's WhatsApp number"""
    order = get_object_or_404(Order, pk=pk)
    
    if not order.customer.phone:
        return JsonResponse({
            'success': False,
            'error': 'Customer has no phone number'
        })
    
    whatsapp_service = WhatsAppService()
    validation_result = whatsapp_service.validate_phone_number(order.customer.phone)
    
    if validation_result['is_valid']:
        # Also check if it's likely to have WhatsApp
        has_whatsapp, whatsapp_message = whatsapp_service.check_whatsapp_business_number(order.customer.phone)
        
        return JsonResponse({
            'success': True,
            'is_valid': True,
            'formatted_number': validation_result['display_format'],
            'is_mobile': validation_result.get('is_mobile', False),
            'has_whatsapp': has_whatsapp,
            'whatsapp_message': whatsapp_message,
            'carrier': validation_result.get('carrier', ''),
            'location': validation_result.get('location', '')
        })
    else:
        return JsonResponse({
            'success': False,
            'is_valid': False,
            'error': validation_result['error']
        })


@login_required 
def generate_whatsapp_share(request, pk):
    """Generate WhatsApp share URL for receipt"""
    order = get_object_or_404(Order, pk=pk)
    
    if not order.customer.phone:
        return JsonResponse({
            'success': False,
            'error': 'Customer has no phone number'
        })
    
    # Get or create receipt
    receipt, created = Receipt.objects.get_or_create(
        order=order,
        defaults={
            'receipt_number': f'REC{order.order_number[3:]}',
            'generated_by': request.user,
            'content': {
                'order_number': order.order_number,
                'customer': order.customer.name,
                'total_amount': float(order.total_amount),
                'payment_method': order.payment_method.name,
                'generated_at': timezone.now().isoformat()
            }
        }
    )
    
    whatsapp_service = WhatsAppService()
    
    # Format message
    message = whatsapp_service.format_receipt_message(order, receipt)
    
    # Generate WhatsApp URL
    use_web = request.GET.get('web', 'false').lower() == 'true'
    whatsapp_url, error = whatsapp_service.generate_whatsapp_url(
        order.customer.phone, 
        message, 
        use_web=use_web
    )
    
    if whatsapp_url:
        return JsonResponse({
            'success': True,
            'whatsapp_url': whatsapp_url,
            'message': message,
            'phone_number': order.customer.phone
        })
    else:
        return JsonResponse({
            'success': False,
            'error': error or 'Could not generate WhatsApp URL'
        })


@login_required
def download_receipt_pdf(request, pk):
    """Generate and download PDF receipt"""
    order = get_object_or_404(Order, pk=pk)
    
    # Get or create receipt
    receipt, created = Receipt.objects.get_or_create(
        order=order,
        defaults={
            'receipt_number': f'REC{order.order_number[3:]}',
            'generated_by': request.user,
            'content': {
                'order_number': order.order_number,
                'customer': order.customer.name,
                'total_amount': float(order.total_amount),
                'payment_method': order.payment_method.name,
                'generated_at': timezone.now().isoformat()
            }
        }
    )
    
    # Generate PDF
    pdf_service = ReceiptPDFService()
    download = request.GET.get('download', 'true').lower() == 'true'
    return pdf_service.generate_receipt_pdf(order, receipt, download=download)


@login_required
def download_receipt_png(request, pk):
    """Generate and download PNG receipt image"""
    order = get_object_or_404(Order, pk=pk)
    
    # Get or create receipt
    receipt, created = Receipt.objects.get_or_create(
        order=order,
        defaults={
            'receipt_number': f'REC{order.order_number[3:]}',
            'generated_by': request.user,
            'content': {
                'order_number': order.order_number,
                'customer': order.customer.name,
                'total_amount': float(order.total_amount),
                'payment_method': order.payment_method.name,
                'generated_at': timezone.now().isoformat()
            }
        }
    )
    
    # Generate PNG
    pdf_service = ReceiptPDFService()
    image_bytes = pdf_service.generate_receipt_image(order, receipt)
    
    # Create response
    filename = f"receipt_{receipt.receipt_number}_{order.order_number}.png"
    response = HttpResponse(image_bytes, content_type='image/png')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


@login_required 
def generate_whatsapp_share_with_attachment(request, pk):
    """Generate WhatsApp share URL with PDF or PNG attachment"""
    order = get_object_or_404(Order, pk=pk)
    format_type = request.GET.get('format', 'text')  # text, pdf, png
    
    if not order.customer.phone:
        return JsonResponse({
            'success': False,
            'error': 'Customer has no phone number'
        })
    
    # Get or create receipt
    receipt, created = Receipt.objects.get_or_create(
        order=order,
        defaults={
            'receipt_number': f'REC{order.order_number[3:]}',
            'generated_by': request.user,
            'content': {
                'order_number': order.order_number,
                'customer': order.customer.name,
                'total_amount': float(order.total_amount),
                'payment_method': order.payment_method.name,
                'generated_at': timezone.now().isoformat()
            }
        }
    )
    
    whatsapp_service = WhatsAppService()
    
    # Format message
    if format_type == 'pdf':
        message = whatsapp_service.format_receipt_message_with_pdf(order, receipt)
        # Generate download URLs
        try:
            pdf_url = request.build_absolute_uri(f'/orders/{pk}/receipt/pdf/?download=true')
        except Exception:
            pdf_url = f'/orders/{pk}/receipt/pdf/?download=true'
        attachment_info = {
            'type': 'pdf',
            'download_url': pdf_url,
            'filename': f"receipt_{receipt.receipt_number}_{order.order_number}.pdf"
        }
    elif format_type == 'png':
        message = whatsapp_service.format_receipt_message_with_image(order, receipt)
        # Generate download URLs
        try:
            png_url = request.build_absolute_uri(f'/orders/{pk}/receipt/png/')
        except Exception:
            png_url = f'/orders/{pk}/receipt/png/'
        attachment_info = {
            'type': 'png',
            'download_url': png_url,
            'filename': f"receipt_{receipt.receipt_number}_{order.order_number}.png"
        }
    else:
        message = whatsapp_service.format_receipt_message(order, receipt)
        attachment_info = None
    
    # Generate WhatsApp URL
    use_web = request.GET.get('web', 'false').lower() == 'true'
    whatsapp_url, error = whatsapp_service.generate_whatsapp_url(
        order.customer.phone, 
        message, 
        use_web=use_web
    )
    
    if whatsapp_url:
        response_data = {
            'success': True,
            'whatsapp_url': whatsapp_url,
            'message': message,
            'phone_number': order.customer.phone,
            'format': format_type
        }
        
        if attachment_info:
            response_data['attachment'] = attachment_info
            
        return JsonResponse(response_data)
    else:
        return JsonResponse({
            'success': False,
            'error': error or 'Could not generate WhatsApp URL'
        })


# API Views
@extend_schema(
    tags=['orders'],
    summary='List and Create Orders',
    description='Retrieve orders with filtering and pagination, or create new laundry orders.',
    parameters=[
        OpenApiParameter(
            name='status',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Filter by order status: pending, in_progress, ready, completed, cancelled'
        ),
        OpenApiParameter(
            name='customer',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Filter by customer ID'
        ),
        OpenApiParameter(
            name='search',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Search by order number, customer name, or phone'
        ),
    ],
    examples=[
        OpenApiExample(
            'Order List Response',
            summary='Paginated order list with details',
            description='List of orders with customer and service information',
            value={
                "count": 45,
                "next": "http://127.0.0.1:8000/orders/api/?page=2",
                "previous": None,
                "results": [
                    {
                        "id": 1,
                        "order_number": "ORD-20250129-001",
                        "customer": {
                            "id": 1,
                            "name": "John Doe",
                            "phone": "+234-800-123-4567"
                        },
                        "status": "pending",
                        "total_amount": "120.00",
                        "created_at": "2025-01-29T10:30:00Z",
                        "expected_completion": "2025-01-31T16:00:00Z",
                        "lines": [
                            {
                                "service": "Dry Cleaning",
                                "pieces": 5,
                                "unit_price": "10.00",
                                "total_price": "50.00"
                            }
                        ]
                    }
                ]
            },
            response_only=True,
        ),
        OpenApiExample(
            'Create Order Request',
            summary='Create new laundry order',
            description='Order creation with customer, services, and delivery details',
            value={
                "customer": 1,
                "lines": [
                    {
                        "service": 1,
                        "pieces": 5,
                        "special_instructions": "Handle with care"
                    }
                ],
                "pickup_date": "2025-01-30",
                "delivery_date": "2025-02-01",
                "special_instructions": "Customer prefers pickup after 5 PM"
            },
            request_only=True,
        ),
    ],
    extensions={
        'x-code-samples': [
            {
                'lang': 'curl',
                'label': 'cURL - List Orders',
                'source': '''curl -X GET "http://127.0.0.1:8000/orders/api/?status=pending&customer=1" \\
  -H "Accept: application/json" \\
  -H "Authorization: Bearer YOUR_JWT_TOKEN"'''
            },
            {
                'lang': 'curl',
                'label': 'cURL - Create Order',
                'source': '''curl -X POST "http://127.0.0.1:8000/orders/api/" \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \\
  -d '{
    "customer": 1,
    "lines": [
      {
        "service": 1,
        "pieces": 5,
        "special_instructions": "Handle with care"
      }
    ],
    "pickup_date": "2025-01-30",
    "delivery_date": "2025-02-01"
  }'
'''
            },
            {
                'lang': 'python',
                'label': 'Python (requests)',
                'source': '''import requests
from datetime import datetime, timedelta

# List orders
url = "http://127.0.0.1:8000/orders/api/"
headers = {
    "Accept": "application/json",
    "Authorization": "Bearer YOUR_JWT_TOKEN"
}
params = {
    "status": "pending",
    "customer": 1
}

response = requests.get(url, headers=headers, params=params)
orders = response.json()
print(f"Found {orders['count']} orders")

# Create new order
order_data = {
    "customer": 1,
    "lines": [
        {
            "service": 1,
            "pieces": 5,
            "special_instructions": "Handle with care"
        }
    ],
    "pickup_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
    "delivery_date": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
}

create_response = requests.post(url, headers=headers, json=order_data)
new_order = create_response.json()
print(f"Created order: {new_order['order_number']}")'''
            },
            {
                'lang': 'javascript',
                'label': 'JavaScript (fetch)',
                'source': '''// List orders
const listUrl = "http://127.0.0.1:8000/orders/api/?status=pending";

fetch(listUrl, {
  method: 'GET',
  headers: {
    'Accept': 'application/json',
    'Authorization': 'Bearer YOUR_JWT_TOKEN'
  }
})
.then(response => response.json())
.then(data => {
  console.log(`Found ${data.count} orders`);
  data.results.forEach(order => {
    console.log(`Order: ${order.order_number} - ${order.status}`);
  });
});

// Create new order
const orderData = {
  customer: 1,
  lines: [
    {
      service: 1,
      pieces: 5,
      special_instructions: "Handle with care"
    }
  ],
  pickup_date: "2025-01-30",
  delivery_date: "2025-02-01"
};

fetch("http://127.0.0.1:8000/orders/api/", {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer YOUR_JWT_TOKEN'
  },
  body: JSON.stringify(orderData)
})
.then(response => response.json())
.then(order => {
  console.log(`Created order: ${order.order_number}`);
});'''
            },
            {
                'lang': 'php',
                'label': 'PHP',
                'source': '''<?php
// List orders
$url = "http://127.0.0.1:8000/orders/api/?status=pending&customer=1";

$headers = array(
    'Accept: application/json',
    'Authorization: Bearer YOUR_JWT_TOKEN'
);

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

$response = curl_exec($ch);
$orders = json_decode($response, true);

echo "Found " . $orders['count'] . " orders\\n";

// Create new order
$orderData = array(
    'customer' => 1,
    'lines' => array(
        array(
            'service' => 1,
            'pieces' => 5,
            'special_instructions' => 'Handle with care'
        )
    ),
    'pickup_date' => date('Y-m-d', strtotime('+1 day')),
    'delivery_date' => date('Y-m-d', strtotime('+3 days'))
);

curl_setopt($ch, CURLOPT_URL, "http://127.0.0.1:8000/orders/api/");
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($orderData));
curl_setopt($ch, CURLOPT_HTTPHEADER, array(
    'Content-Type: application/json',
    'Authorization: Bearer YOUR_JWT_TOKEN'
));

$createResponse = curl_exec($ch);
$newOrder = json_decode($createResponse, true);

echo "Created order: " . $newOrder['order_number'] . "\\n";
curl_close($ch);
?>'''
            },
            {
                'lang': 'csharp',
                'label': 'C#',
                'source': '''using System.Net.Http;
using System.Text;
using System.Text.Json;

public class OrderLine
{
    public int Service { get; set; }
    public int Pieces { get; set; }
    public string SpecialInstructions { get; set; }
}

public class CreateOrderRequest
{
    public int Customer { get; set; }
    public List<OrderLine> Lines { get; set; }
    public string PickupDate { get; set; }
    public string DeliveryDate { get; set; }
}

var client = new HttpClient();
client.DefaultRequestHeaders.Add("Authorization", "Bearer YOUR_JWT_TOKEN");

// List orders
var listResponse = await client.GetAsync(
    "http://127.0.0.1:8000/orders/api/?status=pending"
);

if (listResponse.IsSuccessStatusCode)
{
    var content = await listResponse.Content.ReadAsStringAsync();
    var ordersData = JsonSerializer.Deserialize<dynamic>(content);
    Console.WriteLine($"Found orders");
}

// Create new order
var orderRequest = new CreateOrderRequest
{
    Customer = 1,
    Lines = new List<OrderLine>
    {
        new OrderLine
        {
            Service = 1,
            Pieces = 5,
            SpecialInstructions = "Handle with care"
        }
    },
    PickupDate = DateTime.Now.AddDays(1).ToString("yyyy-MM-dd"),
    DeliveryDate = DateTime.Now.AddDays(3).ToString("yyyy-MM-dd")
};

var json = JsonSerializer.Serialize(orderRequest);
var createContent = new StringContent(json, Encoding.UTF8, "application/json");

var createResponse = await client.PostAsync(
    "http://127.0.0.1:8000/orders/api/", createContent
);

if (createResponse.IsSuccessStatusCode)
{
    var newOrderContent = await createResponse.Content.ReadAsStringAsync();
    Console.WriteLine("Order created successfully");
}'''
            },
            {
                'lang': 'go',
                'label': 'Go',
                'source': '''package main

import (
    "bytes"
    "encoding/json"
    "fmt"
    "net/http"
    "io/ioutil"
    "time"
)

type OrderLine struct {
    Service             int    `json:"service"`
    Pieces              int    `json:"pieces"`
    SpecialInstructions string `json:"special_instructions,omitempty"`
}

type CreateOrderRequest struct {
    Customer     int         `json:"customer"`
    Lines        []OrderLine `json:"lines"`
    PickupDate   string      `json:"pickup_date"`
    DeliveryDate string      `json:"delivery_date"`
}

type OrderResponse struct {
    Count   int `json:"count"`
    Results []map[string]interface{} `json:"results"`
}

func main() {
    client := &http.Client{}
    
    // List orders
    req, _ := http.NewRequest("GET", 
        "http://127.0.0.1:8000/orders/api/?status=pending", nil)
    req.Header.Add("Accept", "application/json")
    req.Header.Add("Authorization", "Bearer YOUR_JWT_TOKEN")
    
    resp, _ := client.Do(req)
    body, _ := ioutil.ReadAll(resp.Body)
    resp.Body.Close()
    
    var orders OrderResponse
    json.Unmarshal(body, &orders)
    fmt.Printf("Found %d orders\\n", orders.Count)
    
    // Create new order
    orderRequest := CreateOrderRequest{
        Customer: 1,
        Lines: []OrderLine{
            {
                Service: 1,
                Pieces:  5,
                SpecialInstructions: "Handle with care",
            },
        },
        PickupDate:   time.Now().AddDate(0, 0, 1).Format("2006-01-02"),
        DeliveryDate: time.Now().AddDate(0, 0, 3).Format("2006-01-02"),
    }
    
    jsonData, _ := json.Marshal(orderRequest)
    
    createReq, _ := http.NewRequest("POST", 
        "http://127.0.0.1:8000/orders/api/", bytes.NewBuffer(jsonData))
    createReq.Header.Set("Content-Type", "application/json")
    createReq.Header.Set("Authorization", "Bearer YOUR_JWT_TOKEN")
    
    createResp, _ := client.Do(createReq)
    defer createResp.Body.Close()
    
    fmt.Println("Order creation request sent")
}'''
            }
        ]
    }
)
class OrderListCreateAPIView(generics.ListCreateAPIView):
    """API view for listing and creating orders"""
    queryset = Order.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_method', 'customer']
    search_fields = ['order_number', 'customer__name', 'customer__phone']
    ordering_fields = ['created_at', 'total_amount', 'expected_completion']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return OrderCreateSerializer
        return OrderListSerializer
    
    def get_queryset(self):
        return Order.objects.select_related(
            'customer', 'created_by'
        ).prefetch_related('lines')


class OrderRetrieveUpdateAPIView(generics.RetrieveUpdateAPIView):
    """API view for retrieving and updating orders"""
    queryset = Order.objects.all()
    serializer_class = OrderDetailSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Order.objects.select_related(
            'customer', 'created_by'
        ).prefetch_related(
            'lines__service__category',
            'status_history__changed_by'
        )


class OrderUpdateStatusAPIView(generics.UpdateAPIView):
    """API view for updating order status only"""
    queryset = Order.objects.all()
    serializer_class = OrderUpdateStatusSerializer
    permission_classes = [IsAuthenticated]


@extend_schema(
    tags=['orders'],
    summary='Order Statistics and Analytics',
    description='Get comprehensive order analytics including revenue, status distribution, and trends.',
    examples=[
        OpenApiExample(
            'Order Statistics Response',
            summary='Complete order analytics dashboard data',
            description='Business intelligence data for order management and revenue tracking',
            value={
                "total_orders": 1250,
                "pending_orders": 45,
                "ready_orders": 15,
                "completed_orders": 1180,
                "cancelled_orders": 10,
                "today_orders": 8,
                "today_revenue": "850.00",
                "monthly_revenue": "15000.00",
                "monthly_orders": 125,
                "monthly_growth": 12.5,
                "average_order_value": "120.00"
            },
            response_only=True,
        ),
    ],
    extensions={
        'x-code-samples': [
            {
                'lang': 'curl',
                'label': 'cURL',
                'source': '''curl -X GET "http://127.0.0.1:8000/orders/api/stats/" \\
  -H "Accept: application/json" \\
  -H "Authorization: Bearer YOUR_JWT_TOKEN"'''
            },
            {
                'lang': 'python',
                'label': 'Python (requests)',
                'source': '''import requests

url = "http://127.0.0.1:8000/orders/api/stats/"
headers = {
    "Accept": "application/json",
    "Authorization": "Bearer YOUR_JWT_TOKEN"
}

response = requests.get(url, headers=headers)
stats = response.json()

print("Order Statistics:")
print(f"Total Orders: {stats['total_orders']}")
print(f"Pending: {stats['pending_orders']}")
print(f"Today's Revenue: ${stats['today_revenue']}")
print(f"Monthly Revenue: ${stats['monthly_revenue']}")
print(f"Monthly Growth: {stats.get('monthly_growth', 0)}%")'''
            },
            {
                'lang': 'javascript',
                'label': 'JavaScript (fetch)',
                'source': '''fetch('http://127.0.0.1:8000/orders/api/stats/', {
  method: 'GET',
  headers: {
    'Accept': 'application/json',
    'Authorization': 'Bearer YOUR_JWT_TOKEN'
  }
})
.then(response => response.json())
.then(stats => {
  console.log('Order Analytics:');
  console.log(`Total Orders: ${stats.total_orders}`);
  console.log(`Pending: ${stats.pending_orders}`);
  console.log(`Ready: ${stats.ready_orders}`);
  console.log(`Today's Revenue: $${stats.today_revenue}`);
  console.log(`Monthly Revenue: $${stats.monthly_revenue}`);
  
  // Display status distribution
  const statusData = {
    pending: stats.pending_orders,
    ready: stats.ready_orders,
    completed: stats.completed_orders
  };
  
  console.log('Status Distribution:', statusData);
});'''
            },
            {
                'lang': 'php',
                'label': 'PHP',
                'source': '''<?php
$url = "http://127.0.0.1:8000/orders/api/stats/";

$headers = array(
    'Accept: application/json',
    'Authorization: Bearer YOUR_JWT_TOKEN'
);

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

$response = curl_exec($ch);
$stats = json_decode($response, true);

echo "Order Statistics:\\n";
echo "Total Orders: " . $stats['total_orders'] . "\\n";
echo "Pending: " . $stats['pending_orders'] . "\\n";
echo "Ready: " . $stats['ready_orders'] . "\\n";
echo "Today's Revenue: $" . $stats['today_revenue'] . "\\n";
echo "Monthly Revenue: $" . $stats['monthly_revenue'] . "\\n";

if (isset($stats['monthly_growth'])) {
    echo "Monthly Growth: " . $stats['monthly_growth'] . "%\\n";
}

curl_close($ch);
?>'''
            },
            {
                'lang': 'csharp',
                'label': 'C#',
                'source': '''using System.Net.Http;
using System.Threading.Tasks;
using Newtonsoft.Json;

public class OrderStats
{
    public int TotalOrders { get; set; }
    public int PendingOrders { get; set; }
    public int ReadyOrders { get; set; }
    public int CompletedOrders { get; set; }
    public int TodayOrders { get; set; }
    public decimal TodayRevenue { get; set; }
    public decimal MonthlyRevenue { get; set; }
    public int MonthlyOrders { get; set; }
    public decimal? MonthlyGrowth { get; set; }
    public decimal AverageOrderValue { get; set; }
}

var client = new HttpClient();
client.DefaultRequestHeaders.Add("Authorization", "Bearer YOUR_JWT_TOKEN");

var response = await client.GetAsync("http://127.0.0.1:8000/orders/api/stats/");

if (response.IsSuccessStatusCode)
{
    var content = await response.Content.ReadAsStringAsync();
    var stats = JsonConvert.DeserializeObject<OrderStats>(content);
    
    Console.WriteLine("Order Statistics:");
    Console.WriteLine($"Total Orders: {stats.TotalOrders}");
    Console.WriteLine($"Pending: {stats.PendingOrders}");
    Console.WriteLine($"Ready: {stats.ReadyOrders}");
    Console.WriteLine($"Today's Revenue: ${stats.TodayRevenue}");
    Console.WriteLine($"Monthly Revenue: ${stats.MonthlyRevenue}");
    
    if (stats.MonthlyGrowth.HasValue)
    {
        Console.WriteLine($"Monthly Growth: {stats.MonthlyGrowth}%");
    }
}'''
            },
            {
                'lang': 'go',
                'label': 'Go',
                'source': '''package main

import (
    "fmt"
    "net/http"
    "io/ioutil"
    "encoding/json"
)

type OrderStats struct {
    TotalOrders       int     `json:"total_orders"`
    PendingOrders     int     `json:"pending_orders"`
    ReadyOrders       int     `json:"ready_orders"`
    CompletedOrders   int     `json:"completed_orders"`
    TodayOrders       int     `json:"today_orders"`
    TodayRevenue      string  `json:"today_revenue"`
    MonthlyRevenue    string  `json:"monthly_revenue"`
    MonthlyOrders     int     `json:"monthly_orders"`
    MonthlyGrowth     *float64 `json:"monthly_growth"`
    AverageOrderValue string  `json:"average_order_value"`
}

func main() {
    client := &http.Client{}
    req, _ := http.NewRequest("GET", 
        "http://127.0.0.1:8000/orders/api/stats/", nil)
    
    req.Header.Add("Accept", "application/json")
    req.Header.Add("Authorization", "Bearer YOUR_JWT_TOKEN")
    
    resp, _ := client.Do(req)
    defer resp.Body.Close()
    
    body, _ := ioutil.ReadAll(resp.Body)
    
    var stats OrderStats
    json.Unmarshal(body, &stats)
    
    fmt.Printf("Order Statistics:\\n")
    fmt.Printf("Total Orders: %d\\n", stats.TotalOrders)
    fmt.Printf("Pending: %d\\n", stats.PendingOrders)
    fmt.Printf("Ready: %d\\n", stats.ReadyOrders)
    fmt.Printf("Today's Revenue: $%s\\n", stats.TodayRevenue)
    fmt.Printf("Monthly Revenue: $%s\\n", stats.MonthlyRevenue)
    
    if stats.MonthlyGrowth != nil {
        fmt.Printf("Monthly Growth: %.1f%%\\n", *stats.MonthlyGrowth)
    }
}'''
            }
        ]
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_stats_api(request):
    """API endpoint for order statistics"""
    today = timezone.now().date()
    
    # Basic stats
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status='pending').count()
    ready_orders = Order.objects.filter(status='ready').count()
    completed_orders = Order.objects.filter(status='completed').count()
    
    # Today's stats
    today_orders = Order.objects.filter(created_at__date=today)
    today_revenue = today_orders.filter(status='completed').aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    # Current month stats
    current_month_start = today.replace(day=1)
    monthly_orders = Order.objects.filter(created_at__date__gte=current_month_start)
    monthly_revenue = monthly_orders.filter(status='completed').aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    # Previous month stats for trend calculation
    prev_month_end = current_month_start - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)
    prev_month_orders = Order.objects.filter(
        created_at__date__gte=prev_month_start,
        created_at__date__lte=prev_month_end
    )
    prev_month_revenue = prev_month_orders.filter(status='completed').aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    # Calculate trends
    revenue_trend = 0
    if prev_month_revenue > 0:
        revenue_trend = ((monthly_revenue - prev_month_revenue) / prev_month_revenue) * 100
    elif monthly_revenue > 0:
        revenue_trend = 100  # If previous month was 0, and current is > 0, that's a 100% increase
    
    return Response({
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'ready_orders': ready_orders,
        'completed_orders': completed_orders,
        'cancelled_orders': Order.objects.filter(status='cancelled').count(),
        'today_orders': today_orders.count(),
        'completed_today': Order.objects.filter(created_at__date=today, status='completed').count(),
        'today_revenue': float(today_revenue),
        'monthly_orders': monthly_orders.count(),
        'monthly_revenue': float(monthly_revenue),
        'prev_month_revenue': float(prev_month_revenue),
        'revenue_trend': round(revenue_trend, 1),
        'average_order_value': float(monthly_revenue / monthly_orders.count()) if monthly_orders.count() > 0 else 0
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_orders_api(request):
    """API endpoint for recent orders"""
    limit = int(request.GET.get('limit', 10))
    orders = Order.objects.select_related(
        'customer', 'created_by'
    ).order_by('-created_at')[:limit]
    
    serializer = OrderListSerializer(orders, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def quick_order_api(request):
    """API endpoint for quick order creation (POS)"""
    import logging
    logger = logging.getLogger(__name__)
    
    # Debug logging
    logger.info(f"Quick order API called by user: {request.user}")
    logger.info(f"Request data: {request.data}")
    
    serializer = OrderCreateSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        order = serializer.save()
        response_serializer = OrderDetailSerializer(order)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    # Debug validation errors
    logger.error(f"Order creation failed with errors: {serializer.errors}")
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@login_required
def get_customer_loyalty_points(request):
    """API endpoint to fetch customer loyalty points."""
    customer_id = request.GET.get('customer_id')
    if not customer_id:
        return JsonResponse({'error': 'Customer ID is required.'}, status=400)
    
    try:
        customer = get_object_or_404(Customer, pk=customer_id)
        return JsonResponse({'loyalty_points': customer.loyalty_points})
    except Customer.DoesNotExist:
        return JsonResponse({'error': 'Customer not found.'}, status=404)
