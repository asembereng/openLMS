from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
import json


class ReportTemplate(models.Model):
    """Templates for different types of reports"""
    REPORT_TYPES = [
        ('daily_sales', 'Daily Sales Report'),
        ('monthly_profit', 'Monthly Profitability Report'),
        ('customer_statement', 'Customer Statement'),
        ('expense_summary', 'Expense Summary'),
        ('service_analysis', 'Service Analysis'),
        ('custom', 'Custom Report'),
    ]
    
    name = models.CharField(max_length=200)
    report_type = models.CharField(max_length=50, choices=REPORT_TYPES)
    description = models.TextField(blank=True)
    
    # Report configuration (JSON format for flexibility)
    config = models.JSONField(
        default=dict,
        help_text="Report configuration including filters, columns, etc."
    )
    
    # Access control
    is_public = models.BooleanField(
        default=False,
        help_text="If True, all users can access this template"
    )
    allowed_roles = models.JSONField(
        default=list,
        help_text="List of roles that can access this template"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='report_templates_created'
    )
    
    class Meta:
        verbose_name = 'Report Template'
        verbose_name_plural = 'Report Templates'
        ordering = ['report_type', 'name']
        
    def __str__(self):
        return f"{self.get_report_type_display()} - {self.name}"
    
    def can_be_accessed_by(self, user):
        """Check if user can access this report template"""
        if self.is_public:
            return True
            
        if hasattr(user, 'profile'):
            return user.profile.role in self.allowed_roles
            
        return False


class GeneratedReport(models.Model):
    """Track generated reports for audit and caching"""
    template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.CASCADE,
        related_name='generated_reports'
    )
    title = models.CharField(max_length=255)
    
    # Report parameters
    parameters = models.JSONField(
        default=dict,
        help_text="Parameters used to generate this report"
    )
    
    # Date range
    date_from = models.DateField(null=True, blank=True)
    date_to = models.DateField(null=True, blank=True)
    
    # Report data (JSON format)
    data = models.JSONField(
        default=dict,
        help_text="Generated report data"
    )
    
    # Export tracking
    export_formats = models.JSONField(
        default=list,
        help_text="List of formats this report was exported to"
    )
    
    # Status
    STATUS_CHOICES = [
        ('generating', 'Generating'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='generating')
    error_message = models.TextField(blank=True)
    
    # Performance tracking
    generation_time = models.DurationField(null=True, blank=True)
    data_size = models.PositiveIntegerField(null=True, blank=True, help_text="Size in bytes")
    
    # Audit fields
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='reports_generated'
    )
    
    # Cache expiry
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this report cache expires"
    )
    
    class Meta:
        verbose_name = 'Generated Report'
        verbose_name_plural = 'Generated Reports'
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['template', '-generated_at']),
            models.Index(fields=['generated_by', '-generated_at']),
            models.Index(fields=['status']),
        ]
        
    def __str__(self):
        return f"{self.title} - {self.generated_at.strftime('%Y-%m-%d %H:%M')}"
    
    def is_expired(self):
        """Check if the report cache has expired"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    def get_summary(self):
        """Get report summary statistics"""
        try:
            data = self.data
            if isinstance(data, str):
                data = json.loads(data)
            return data.get('summary', {})
        except (json.JSONDecodeError, AttributeError):
            return {}


class ReportSchedule(models.Model):
    """Scheduled report generation"""
    template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.CASCADE,
        related_name='schedules'
    )
    name = models.CharField(max_length=200)
    
    # Schedule configuration
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
    ]
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    
    # Time settings
    run_time = models.TimeField(default='09:00:00')
    timezone = models.CharField(max_length=50, default='Africa/Lagos')
    
    # Recipients
    email_recipients = models.JSONField(
        default=list,
        help_text="List of email addresses to send reports to"
    )
    
    # Report parameters
    parameters = models.JSONField(
        default=dict,
        help_text="Default parameters for scheduled reports"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='report_schedules_created'
    )
    
    class Meta:
        verbose_name = 'Report Schedule'
        verbose_name_plural = 'Report Schedules'
        ordering = ['name']
        
    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()})"


class ReportExport(models.Model):
    """Track report exports"""
    report = models.ForeignKey(
        GeneratedReport,
        on_delete=models.CASCADE,
        related_name='exports'
    )
    
    EXPORT_FORMATS = [
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('csv', 'CSV'),
        ('json', 'JSON'),
    ]
    format = models.CharField(max_length=10, choices=EXPORT_FORMATS)
    
    # File details
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text="Size in bytes")
    file_path = models.CharField(max_length=500, blank=True)
    
    # Download tracking
    download_count = models.PositiveIntegerField(default=0)
    last_downloaded = models.DateTimeField(null=True, blank=True)
    
    # Audit fields
    exported_at = models.DateTimeField(auto_now_add=True)
    exported_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='report_exports'
    )
    
    class Meta:
        verbose_name = 'Report Export'
        verbose_name_plural = 'Report Exports'
        ordering = ['-exported_at']
        
    def __str__(self):
        return f"{self.report.title} - {self.get_format_display()}"
    
    def record_download(self):
        """Record a download event"""
        self.download_count += 1
        self.last_downloaded = timezone.now()
        self.save(update_fields=['download_count', 'last_downloaded'])
