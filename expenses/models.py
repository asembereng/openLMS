from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
from django.urls import reverse


class ExpenseCategory(models.Model):
    """Categories for expenses (e.g., Detergent, Salaries, Utilities)"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Font Awesome icon class")
    color = models.CharField(max_length=7, default='#6c757d', help_text="Hex color code for charts")
    is_active = models.BooleanField(default=True)
    
    # Budget tracking
    monthly_budget = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional monthly budget limit"
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.PROTECT,
        related_name='expense_categories_created'
    )
    
    class Meta:
        verbose_name = 'Expense Category'
        verbose_name_plural = 'Expense Categories'
        ordering = ['name']
        
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('expenses:category_detail', kwargs={'pk': self.pk})
    
    def get_monthly_total(self, year, month):
        """Get total expenses for a specific month"""
        return self.expenses.filter(
            expense_date__year=year,
            expense_date__month=month
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
    
    def get_budget_usage_percentage(self, year, month):
        """Get budget usage percentage for a specific month"""
        if not self.monthly_budget:
            return None
        
        total = self.get_monthly_total(year, month)
        return (total / self.monthly_budget * 100) if self.monthly_budget > 0 else 0


class Expense(models.Model):
    """Individual expense records"""
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name='expenses'
    )
    description = models.CharField(max_length=255)
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    expense_date = models.DateField(default=timezone.now)
    
    # Supporting documentation
    receipt_image = models.ImageField(
        upload_to='expense_receipts/%Y/%m/',
        null=True,
        blank=True,
        help_text="Upload receipt image"
    )
    notes = models.TextField(blank=True)
    
    # Status
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expenses_approved'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.PROTECT,
        related_name='expenses_created'
    )
    
    class Meta:
        verbose_name = 'Expense'
        verbose_name_plural = 'Expenses'
        ordering = ['-expense_date', '-created_at']
        indexes = [
            models.Index(fields=['category', '-expense_date']),
            models.Index(fields=['-expense_date']),
            models.Index(fields=['created_by', '-expense_date']),
        ]
        
    def __str__(self):
        from system_settings.models import SystemConfiguration
        config = SystemConfiguration.get_config()
        return f"{self.category.name} - {self.description} ({config.currency_symbol}{self.amount})"
    
    def get_absolute_url(self):
        return reverse('expenses:detail', kwargs={'pk': self.pk})
    
    def approve(self, approved_by):
        """Approve the expense"""
        self.is_approved = True
        self.approved_by = approved_by
        self.approved_at = timezone.now()
        self.save(update_fields=['is_approved', 'approved_by', 'approved_at'])
    
    def can_be_edited_by(self, user):
        """Check if user can edit this expense"""
        # Admins can edit any expense
        if hasattr(user, 'profile') and user.profile.is_admin:
            return True
        
        # Users can edit their own expenses if not approved
        if self.created_by == user and not self.is_approved:
            return True
            
        return False
    
    def can_be_deleted_by(self, user):
        """Check if user can delete this expense"""
        # Only admins can delete expenses
        if hasattr(user, 'profile') and user.profile.is_admin:
            return True
            
        return False

    def can_be_approved_by(self, user):
        """
        Check if the user can approve this expense.
        Only admin users (user.profile.is_admin) can approve and only if the expense is not already approved.
        """
        if not hasattr(user, 'profile'):
            return False
        return user.profile.is_admin and not self.is_approved


class ExpenseAttachment(models.Model):
    """Additional attachments for expenses"""
    expense = models.ForeignKey(
        Expense,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    file = models.FileField(
        upload_to='expense_attachments/%Y/%m/',
        help_text="Additional supporting documents"
    )
    description = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        'auth.User',
        on_delete=models.PROTECT,
        related_name='expense_attachments_uploaded'
    )
    
    class Meta:
        verbose_name = 'Expense Attachment'
        verbose_name_plural = 'Expense Attachments'
        ordering = ['-uploaded_at']
        
    def __str__(self):
        return f"Attachment for {self.expense.description}"


class ExpenseApprovalRequest(models.Model):
    """Track expense approval requests"""
    expense = models.ForeignKey(
        Expense,
        on_delete=models.CASCADE,
        related_name='approval_requests'
    )
    requested_by = models.ForeignKey(
        'auth.User',
        on_delete=models.PROTECT,
        related_name='expense_approval_requests'
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    message = models.TextField(blank=True)
    
    # Response
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    responded_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expense_approval_responses'
    )
    responded_at = models.DateTimeField(null=True, blank=True)
    response_message = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Expense Approval Request'
        verbose_name_plural = 'Expense Approval Requests'
        ordering = ['-requested_at']
        
    def __str__(self):
        return f"Approval request for {self.expense.description} - {self.status}"
