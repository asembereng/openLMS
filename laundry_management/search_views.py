"""
Global search functionality
"""
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.urls import reverse

from orders.models import Order
from customers.models import Customer
from services.models import Service


@login_required
def global_search_api(request):
    """
    Global search API that searches across orders, customers, and services
    """
    query = request.GET.get('q', '').strip()
    
    if not query or len(query) < 2:
        return JsonResponse({'results': []})
    
    results = []
    
    # Search orders
    orders = Order.objects.filter(
        Q(order_number__icontains=query) |
        Q(customer__name__icontains=query) |
        Q(customer__phone__icontains=query)
    ).select_related('customer').order_by('-created_at')[:5]
    
    for order in orders:
        results.append({
            'type': 'order',
            'title': f"Order {order.order_number}",
            'subtitle': f"{order.customer.name} • {order.get_status_display()} • {order.created_at.strftime('%b %d, %Y')}",
            'url': reverse('orders:detail', args=[order.pk])
        })
    
    # Search customers
    customers = Customer.objects.filter(
        Q(name__icontains=query) |
        Q(phone__icontains=query) |
        Q(email__icontains=query)
    ).filter(is_active=True).order_by('name')[:5]
    
    for customer in customers:
        phone_text = f" • {customer.phone}" if customer.phone else ""
        results.append({
            'type': 'customer',
            'title': customer.name,
            'subtitle': f"Customer{phone_text} • {customer.total_orders} orders",
            'url': reverse('customers:detail', args=[customer.pk])
        })
    
    # Search services
    services = Service.objects.filter(
        Q(name__icontains=query) |
        Q(description__icontains=query) |
        Q(category__name__icontains=query)
    ).filter(is_active=True).select_related('category').order_by('name')[:5]
    
    for service in services:
        category_text = f" • {service.category.name}" if service.category else ""
        results.append({
            'type': 'service',
            'title': service.name,
            'subtitle': f"Service{category_text} • {service.price_per_dozen:,.2f} per dozen",
            'url': reverse('services:detail', args=[service.pk])
        })
    
    # Limit total results to 15
    results = results[:15]
    
    return JsonResponse({'results': results})
