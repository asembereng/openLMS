from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
from django.urls import reverse


class ServiceCategory(models.Model):
    """Categories for services (e.g., Washing, Ironing, Dry Cleaning)"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Font Awesome icon class")
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Service Category'
        verbose_name_plural = 'Service Categories'
        ordering = ['display_order', 'name']
        
    def __str__(self):
        return self.name


class Service(models.Model):
    """Services offered by the laundry"""
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.PROTECT,
        related_name='services'
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Pricing per dozen pieces (as per business rules)
    price_per_dozen = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Price for 12 pieces"
    )
    
    # Status and display
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.PROTECT,
        related_name='services_created'
    )
    
    class Meta:
        verbose_name = 'Service'
        verbose_name_plural = 'Services'
        ordering = ['category__display_order', 'display_order', 'name']
        unique_together = ['category', 'name']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['category', 'is_active']),
        ]
        
    def __str__(self):
        return f"{self.category.name} - {self.name}"
    
    def get_absolute_url(self):
        return reverse('services:detail', kwargs={'pk': self.pk})
    
    @property
    def unit_price(self):
        """Calculate unit price per piece (price_per_dozen / 12)"""
        return self.price_per_dozen / 12
    
    def calculate_total(self, pieces):
        """Calculate total price for given number of pieces"""
        from django.conf import settings
        total = self.unit_price * pieces
        
        # Apply rounding strategy from settings
        rounding_strategy = getattr(settings, 'ROUNDING_STRATEGY', 'normal')
        decimal_places = getattr(settings, 'DECIMAL_PLACES', 2)
        
        if rounding_strategy == 'up_to_50':
            # Round up to next 50 bututs/cents
            total = (total * 100).quantize(Decimal('50'), rounding='ROUND_UP') / 100
        else:
            # Normal rounding
            total = total.quantize(Decimal('0.01'), rounding='ROUND_HALF_UP')
            
        return total


class ServicePriceHistory(models.Model):
    """Track service price changes for historical accuracy"""
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='price_history'
    )
    price_per_dozen = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    effective_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.PROTECT,
        related_name='price_changes'
    )
    change_reason = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Service Price History'
        verbose_name_plural = 'Service Price Histories'
        ordering = ['-effective_date']
        indexes = [
            models.Index(fields=['service', '-effective_date']),
        ]
        
    def __str__(self):
        from system_settings.models import SystemConfiguration
        config = SystemConfiguration.get_config()
        return f"{self.service.name} - {config.currency_symbol}{self.price_per_dozen} (from {self.effective_date.date()})"
    
    @property
    def unit_price(self):
        """Calculate unit price per piece for this historical price"""
        return self.price_per_dozen / 12
