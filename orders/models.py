from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
from django.urls import reverse
import uuid


class Order(models.Model):
    """Main order model for POS operations"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('ready', 'Ready'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('delivered', 'Delivered'),
    ]
    
    # Order identification
    order_number = models.CharField(max_length=20, unique=True, editable=False)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Customer and staff
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.PROTECT,
        related_name='orders'
    )
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.PROTECT,
        related_name='orders_created'
    )
    
    # Order details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.ForeignKey(
        'system_settings.PaymentMethod',
        on_delete=models.PROTECT,
        related_name='orders',
        help_text="Payment method used for this order"
    )
    
    # For backward compatibility, we'll also keep the old field with a different name
    # This will be populated during migration and can be removed later
    payment_method_legacy = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        help_text="Legacy payment method field for migration purposes"
    )
    
    # Pricing
    subtotal = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    loyalty_discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Discount applied from loyalty points"
    )
    redeemed_points = models.PositiveIntegerField(
        default=0,
        help_text="Number of loyalty points redeemed for this order"
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Dates
    expected_completion = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    # Additional info
    notes = models.TextField(blank=True)
    special_instructions = models.TextField(blank=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['customer', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['-created_at']),
        ]
        
    def __str__(self):
        return f"Order {self.order_number} - {self.customer.name}"
    
    def get_absolute_url(self):
        return reverse('orders:detail', kwargs={'pk': self.pk})
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        
        # Only calculate totals if the order has a primary key (has been saved before)
        # or if we're explicitly told to skip calculation
        skip_calculation = kwargs.pop('skip_calculation', False)
        if not skip_calculation and self.pk:
            self.calculate_totals()
        
        super().save(*args, **kwargs)
    
    def generate_order_number(self):
        """Generate unique order number"""
        from django.utils import timezone
        now = timezone.now()
        date_part = now.strftime('%Y%m%d')
        
        # Get last order number for today
        last_order = Order.objects.filter(
            order_number__startswith=f'ORD{date_part}'
        ).order_by('-order_number').first()
        
        if last_order:
            last_seq = int(last_order.order_number[-4:])
            new_seq = last_seq + 1
        else:
            new_seq = 1
            
        return f'ORD{date_part}{new_seq:04d}'
    
    def calculate_totals(self):
        """Calculate order totals"""
        # Only calculate if the order has been saved (has a primary key)
        if not self.pk:
            self.subtotal = Decimal('0.00')
            self.discount_amount = Decimal('0.00')
            self.total_amount = Decimal('0.00')
            return
            
        # Calculate subtotal from order lines
        self.subtotal = sum(line.line_total for line in self.lines.all()) or Decimal('0.00')
        
        # Calculate discount
        if self.discount_percentage > 0:
            self.discount_amount = (self.subtotal * self.discount_percentage / 100).quantize(
                Decimal('0.01'), rounding='ROUND_HALF_UP'
            )
        else:
            self.discount_amount = Decimal('0.00')
        
        # Calculate total, subtracting both percentage discount and loyalty discount
        self.total_amount = self.subtotal - self.discount_amount - self.loyalty_discount_amount
    
    @property
    def total_discount(self):
        """Total discount including percentage and loyalty"""
        return self.discount_amount + self.loyalty_discount_amount

    @property
    def total_pieces(self):
        """Total number of pieces in the order"""
        if not self.pk:
            return 0
        return sum(line.pieces for line in self.lines.all())
    
    @property
    def can_be_cancelled(self):
        """Check if order can be cancelled"""
        return self.status in ['pending', 'in_progress']
    
    def mark_completed(self):
        """Mark order as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at'])
        
        # Update customer loyalty stats
        self.customer.update_loyalty_stats()


class OrderLine(models.Model):
    """Individual service lines within an order"""
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='lines'
    )
    service = models.ForeignKey(
        'services.Service',
        on_delete=models.PROTECT,
        related_name='order_lines'
    )
    pieces = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    
    # Pricing (stored for historical accuracy)
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Price per piece at time of order"
    )
    line_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Total for this line (pieces × unit_price)"
    )
    
    # Special requirements
    notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Order Line'
        verbose_name_plural = 'Order Lines'
        ordering = ['id']
        
    def __str__(self):
        return f"{self.order.order_number} - {self.service.name} ({self.pieces} pcs)"
    
    def save(self, *args, **kwargs):
        if not self.unit_price:
            self.unit_price = self.service.unit_price
        self.line_total = self.service.calculate_total(self.pieces)
        super().save(*args, **kwargs)


class OrderStatusHistory(models.Model):
    """Track order status changes"""
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    old_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(
        'auth.User',
        on_delete=models.PROTECT,
        related_name='status_changes'
    )
    notes = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Order Status History'
        verbose_name_plural = 'Order Status Histories'
        ordering = ['-timestamp']
        
    def __str__(self):
        return f"{self.order.order_number}: {self.old_status} → {self.new_status}"


class Receipt(models.Model):
    """Generated receipts for orders"""
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='receipt'
    )
    receipt_number = models.CharField(max_length=20, unique=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(
        'auth.User',
        on_delete=models.PROTECT,
        related_name='receipts_generated'
    )
    
    # Receipt content (JSON format for flexibility)
    content = models.JSONField()
    
    # Email/SMS settings
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    sms_sent = models.BooleanField(default=False)
    sms_sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Receipt'
        verbose_name_plural = 'Receipts'
        ordering = ['-generated_at']
        
    def __str__(self):
        return f"Receipt {self.receipt_number} for {self.order.order_number}"
