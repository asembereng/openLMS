from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from django.contrib.auth.models import User
from .models import ReportTemplate, GeneratedReport, ReportSchedule, ReportExport
import json


class ReportTemplateSerializer(serializers.ModelSerializer):
    """Serializer for report templates"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    generated_count = serializers.SerializerMethodField()
    can_access = serializers.SerializerMethodField()
    
    class Meta:
        model = ReportTemplate
        fields = [
            'id', 'name', 'report_type', 'description', 'config',
            'is_public', 'allowed_roles', 'is_active',
            'created_at', 'updated_at', 'created_by', 'created_by_name',
            'generated_count', 'can_access'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by']
    
    @extend_schema_field(serializers.IntegerField())
    def get_generated_count(self, obj):
        """Get number of times this template has been generated"""
        return obj.generated_reports.count()
    
    @extend_schema_field(serializers.BooleanField())
    def get_can_access(self, obj):
        """Check if current user can access this template"""
        request = self.context.get('request')
        return obj.can_be_accessed_by(request.user) if request else False
    
    def validate_config(self, value):
        """Validate report configuration"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Config must be a valid JSON object.")
        return value
    
    def validate_allowed_roles(self, value):
        """Validate allowed roles"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Allowed roles must be a list.")
        
        valid_roles = ['admin', 'user']  # Add more roles as needed
        for role in value:
            if role not in valid_roles:
                raise serializers.ValidationError(f"Invalid role: {role}")
        
        return value


class ReportTemplateListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for template lists"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    report_type_display = serializers.CharField(source='get_report_type_display', read_only=True)
    
    class Meta:
        model = ReportTemplate
        fields = [
            'id', 'name', 'report_type', 'report_type_display', 'description', 'is_active',
            'created_at', 'created_by_name'
        ]


class GeneratedReportSerializer(serializers.ModelSerializer):
    """Serializer for generated reports"""
    template_name = serializers.CharField(source='template.name', read_only=True)
    template_type = serializers.CharField(source='template.get_report_type_display', read_only=True)
    generated_by_name = serializers.CharField(source='generated_by.get_full_name', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    summary = serializers.SerializerMethodField()
    export_count = serializers.SerializerMethodField()
    
    class Meta:
        model = GeneratedReport
        fields = [
            'id', 'template', 'template_name', 'template_type', 'title',
            'parameters', 'date_from', 'date_to', 'data', 'export_formats',
            'status', 'error_message', 'generation_time', 'data_size',
            'generated_at', 'generated_by', 'generated_by_name',
            'expires_at', 'is_expired', 'summary', 'export_count'
        ]
        read_only_fields = [
            'generated_at', 'generated_by', 'generation_time', 'data_size',
            'status', 'error_message'
        ]
    
    @extend_schema_field(serializers.DictField())
    def get_summary(self, obj):
        """Get report summary statistics"""
        return obj.get_summary()
    
    @extend_schema_field(serializers.IntegerField())
    def get_export_count(self, obj):
        """Get number of exports for this report"""
        return obj.exports.count()


class GeneratedReportListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for report lists"""
    template_name = serializers.CharField(source='template.name', read_only=True)
    template_type = serializers.CharField(source='template.get_report_type_display', read_only=True)
    generated_by_name = serializers.CharField(source='generated_by.get_full_name', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = GeneratedReport
        fields = [
            'id', 'template', 'template_name', 'template_type', 'title',
            'status', 'generated_at', 'generated_by_name', 'expires_at',
            'is_expired', 'data_size'
        ]


class ReportGenerationRequestSerializer(serializers.Serializer):
    """Serializer for report generation requests"""
    template_id = serializers.IntegerField()
    title = serializers.CharField(max_length=255, required=False)
    parameters = serializers.JSONField(default=dict)
    date_from = serializers.DateField(required=False, allow_null=True)
    date_to = serializers.DateField(required=False, allow_null=True)
    export_format = serializers.ChoiceField(
        choices=['pdf', 'excel', 'csv', 'json'],
        required=False,
        allow_null=True
    )
    
    def validate_template_id(self, value):
        """Validate template exists and user has access"""
        try:
            template = ReportTemplate.objects.get(id=value, is_active=True)
        except ReportTemplate.DoesNotExist:
            raise serializers.ValidationError("Template not found or inactive.")
        
        request = self.context.get('request')
        if request and not template.can_be_accessed_by(request.user):
            raise serializers.ValidationError("You don't have access to this template.")
        
        return value
    
    def validate(self, attrs):
        """Validate date range"""
        date_from = attrs.get('date_from')
        date_to = attrs.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise serializers.ValidationError("Date from must be before date to.")
        
        return attrs


class ReportScheduleSerializer(serializers.ModelSerializer):
    """Serializer for report schedules"""
    template_name = serializers.CharField(source='template.name', read_only=True)
    template_type = serializers.CharField(source='template.get_report_type_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    next_run_display = serializers.SerializerMethodField()
    
    class Meta:
        model = ReportSchedule
        fields = [
            'id', 'template', 'template_name', 'template_type', 'name',
            'frequency', 'run_time', 'timezone', 'email_recipients',
            'parameters', 'is_active', 'last_run', 'next_run',
            'next_run_display', 'created_at', 'updated_at',
            'created_by', 'created_by_name'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'last_run', 'next_run']
    
    @extend_schema_field(serializers.CharField())
    def get_next_run_display(self, obj):
        """Get formatted next run time"""
        if obj.next_run:
            return obj.next_run.strftime('%Y-%m-%d %H:%M')
        return None
    
    def validate_email_recipients(self, value):
        """Validate email recipients"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Email recipients must be a list.")
        
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        
        for email in value:
            try:
                validate_email(email)
            except ValidationError:
                raise serializers.ValidationError(f"Invalid email address: {email}")
        
        return value


class ReportExportSerializer(serializers.ModelSerializer):
    """Serializer for report exports"""
    report_title = serializers.CharField(source='report.title', read_only=True)
    exported_by_name = serializers.CharField(source='exported_by.get_full_name', read_only=True)
    file_size_display = serializers.SerializerMethodField()
    
    class Meta:
        model = ReportExport
        fields = [
            'id', 'report', 'report_title', 'format', 'file_name',
            'file_size', 'file_size_display', 'file_path',
            'download_count', 'last_downloaded', 'exported_at',
            'exported_by', 'exported_by_name'
        ]
        read_only_fields = [
            'exported_at', 'exported_by', 'download_count', 'last_downloaded'
        ]
    
    @extend_schema_field(serializers.CharField())
    def get_file_size_display(self, obj):
        """Get human-readable file size"""
        size = obj.file_size
        if size < 1024:
            return f"{size} bytes"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"


class ReportStatsSerializer(serializers.Serializer):
    """Serializer for report statistics"""
    total_templates = serializers.IntegerField()
    active_templates = serializers.IntegerField()
    total_generated = serializers.IntegerField()
    total_exports = serializers.IntegerField()
    active_schedules = serializers.IntegerField()
    popular_templates = serializers.ListField(child=serializers.DictField())
    generation_trend = serializers.ListField(child=serializers.DictField())
    export_formats = serializers.ListField(child=serializers.DictField())
