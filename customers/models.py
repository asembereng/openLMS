from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
from django.urls import reverse
from decimal import Decimal


class Customer(models.Model):
    """Customer model for laundry services"""
    name = models.CharField(max_length=200)
    phone = models.CharField(
        max_length=20,
        validators=[RegexValidator(r'^\+?[\d\s\-\(\)]+$', 'Enter a valid phone number')],
        unique=True
    )
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True)
    date_of_birth = models.DateField(blank=True, null=True, help_text="Customer's date of birth for birthday rewards.")
    notes = models.TextField(blank=True, help_text="Additional notes about the customer")
    
    # Loyalty tracking
    loyalty_points = models.PositiveIntegerField(default=0, help_text="Current loyalty points balance.")
    total_orders = models.PositiveIntegerField(default=0)
    total_spent = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    last_visit = models.DateTimeField(null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.PROTECT,
        related_name='customers_created'
    )
    
    class Meta:
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'
        ordering = ['-last_visit', 'name']
        indexes = [
            models.Index(fields=['phone']),
            models.Index(fields=['name']),
            models.Index(fields=['-last_visit']),
        ]
        
    def __str__(self):
        return f"{self.name} ({self.phone})"
    
    def get_absolute_url(self):
        return reverse('customers:detail', kwargs={'pk': self.pk})
    
    @property
    def display_name(self):
        """Display name with phone for UI"""
        return f"{self.name} - {self.phone}"
    
    def update_loyalty_stats(self):
        """Update loyalty statistics from orders"""
        from orders.models import Order
        orders = Order.objects.filter(customer=self, status='completed')
        self.total_orders = orders.count()
        self.total_spent = sum(order.total_amount for order in orders)
        latest_order = orders.order_by('-created_at').first()
        if latest_order:
            self.last_visit = latest_order.created_at
        self.save(update_fields=['total_orders', 'total_spent', 'last_visit'])


class CustomerNote(models.Model):
    """Additional notes for customers"""
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='customer_notes'
    )
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.PROTECT,
        related_name='customer_notes_created'
    )
    
    class Meta:
        verbose_name = 'Customer Note'
        verbose_name_plural = 'Customer Notes'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Note for {self.customer.name} by {self.created_by.username}"


class CustomerMergeHistory(models.Model):
    """Track customer merge operations"""
    primary_customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='merge_history_as_primary'
    )
    merged_customer_name = models.CharField(max_length=200)
    merged_customer_phone = models.CharField(max_length=20, blank=True)
    merged_customer_email = models.EmailField(blank=True)
    merged_customer_address = models.TextField(blank=True)
    
    # Merge details
    merged_orders_count = models.PositiveIntegerField(default=0)
    merged_notes_count = models.PositiveIntegerField(default=0)
    merge_reason = models.TextField(blank=True)
    
    # Audit fields
    merged_at = models.DateTimeField(auto_now_add=True)
    merged_by = models.ForeignKey(
        'auth.User',
        on_delete=models.PROTECT,
        related_name='customer_merges'
    )
    
    class Meta:
        verbose_name = 'Customer Merge History'
        verbose_name_plural = 'Customer Merge Histories'
        ordering = ['-merged_at']
        
    def __str__(self):
        return f"Merged {self.merged_customer_name} into {self.primary_customer.name}"
