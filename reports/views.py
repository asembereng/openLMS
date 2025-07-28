from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponse, Http404
from django.shortcuts import redirect  # for redirect
from django.utils import timezone
from django.db.models import Count, Sum, Q
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, FormView
from django.urls import reverse_lazy
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.conf import settings
from decimal import Decimal
from datetime import datetime, timedelta
import json
import io
import csv

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from .models import ReportTemplate, GeneratedReport, ReportSchedule, ReportExport
from .serializers import (
    ReportTemplateSerializer, ReportTemplateListSerializer,
    GeneratedReportSerializer, GeneratedReportListSerializer,
    ReportGenerationRequestSerializer, ReportScheduleSerializer,
    ReportExportSerializer, ReportStatsSerializer
)
from .forms import ReportGenerationForm
from .services import ReportGenerationService, ReportExportService


# =============================================================================
# API Views (DRF ViewSets)
# =============================================================================

class ReportTemplateViewSet(viewsets.ModelViewSet):
    """API ViewSet for report templates"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ReportTemplateListSerializer
        return ReportTemplateSerializer
    
    def get_queryset(self):
        queryset = ReportTemplate.objects.select_related('created_by')
        
        # Filter by user access
        user = self.request.user
        if hasattr(user, 'profile'):
            if user.profile.is_admin:
                # Admins can see all templates
                pass
            else:
                # Regular users can only see public templates or templates they have access to
                queryset = queryset.filter(
                    Q(is_public=True) |
                    Q(allowed_roles__contains=[user.profile.role])
                )
        
        # Filter by type
        report_type = self.request.query_params.get('type')
        if report_type:
            queryset = queryset.filter(report_type=report_type)
        
        # Filter by active status
        if self.request.query_params.get('active_only') == 'true':
            queryset = queryset.filter(is_active=True)
        
        return queryset.order_by('report_type', 'name')
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        """Generate a report from this template"""
        template = self.get_object()
        
        # Check access permissions
        if not template.can_be_accessed_by(request.user):
            return Response(
                {'error': 'You do not have access to this template.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate request data
        serializer = ReportGenerationRequestSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        try:
            # Generate report
            service = ReportGenerationService()
            report = service.generate_report(
                template=template,
                user=request.user,
                title=serializer.validated_data.get('title'),
                parameters=serializer.validated_data.get('parameters', {}),
                date_from=serializer.validated_data.get('date_from'),
                date_to=serializer.validated_data.get('date_to')
            )
            
            # Export if format specified
            export_format = serializer.validated_data.get('export_format')
            if export_format:
                export_service = ReportExportService()
                export = export_service.create_export_record(report, export_format, request.user)
                response_data = {
                    'report': GeneratedReportSerializer(report).data,
                    'export': ReportExportSerializer(export).data,
                    'download_url': f'/reports/export/{export.id}/download/'
                }
            else:
                response_data = {
                    'report': GeneratedReportSerializer(report).data
                }
            
            return Response(response_data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response(
                {'error': f'Report generation failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GeneratedReportViewSet(viewsets.ReadOnlyModelViewSet):
    """API ViewSet for generated reports (read-only)"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return GeneratedReportListSerializer
        return GeneratedReportSerializer
    
    def get_queryset(self):
        queryset = GeneratedReport.objects.select_related(
            'template', 'generated_by'
        ).prefetch_related('exports')
        
        # Filter out expired reports by default
        show_expired = self.request.query_params.get('show_expired', 'false').lower() == 'true'
        if not show_expired:
            queryset = queryset.filter(
                Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
            )
        
        # Filter by user access
        user = self.request.user
        if hasattr(user, 'profile') and not user.profile.is_admin:
            # Regular users can only see their own reports
            queryset = queryset.filter(generated_by=user)
        
        # Filter by template
        template = self.request.query_params.get('template')
        if template:
            queryset = queryset.filter(template_id=template)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by date range
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        
        if date_from:
            queryset = queryset.filter(generated_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(generated_at__date__lte=date_to)
        
        return queryset.order_by('-generated_at')
    
    @action(detail=True, methods=['post'])
    def export(self, request, pk=None):
        """Export a generated report"""
        report = self.get_object()
        
        export_format = request.data.get('format')
        if not export_format:
            return Response(
                {'error': 'Export format is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if export_format not in ['pdf', 'excel', 'csv', 'json']:
            return Response(
                {'error': 'Invalid export format.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            service = ReportExportService()
            export = service.create_export_record(report, export_format, request.user)
            
            return Response({
                'export': ReportExportSerializer(export).data,
                'download_url': f'/reports/export/{export.id}/download/',
                'message': 'Report export prepared successfully. Use the download_url to download the file.'
            })
        
        except Exception as e:
            return Response(
                {'error': f'Export failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get report generation statistics"""
        queryset = self.get_queryset()
        
        # Calculate statistics
        total_generated = queryset.count()
        completed_reports = queryset.filter(status='completed').count()
        failed_reports = queryset.filter(status='failed').count()
        
        # Template usage
        template_usage = list(
            queryset.values('template__name', 'template__report_type')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )
        
        # Generation trend (last 30 days)
        generation_trend = []
        for i in range(30):
            date = timezone.now().date() - timedelta(days=i)
            count = queryset.filter(generated_at__date=date).count()
            generation_trend.append({
                'date': date.strftime('%Y-%m-%d'),
                'count': count
            })
        generation_trend.reverse()
        
        # Export format breakdown
        export_formats = list(
            ReportExport.objects.values('format')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        
        stats_data = {
            'total_generated': total_generated,
            'completed_reports': completed_reports,
            'failed_reports': failed_reports,
            'template_usage': template_usage,
            'generation_trend': generation_trend,
            'export_formats': export_formats
        }
        
        return Response(stats_data)


class ReportScheduleViewSet(viewsets.ModelViewSet):
    """API ViewSet for report schedules"""
    serializer_class = ReportScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = ReportSchedule.objects.select_related('template', 'created_by')
        
        # Filter by user access
        user = self.request.user
        if hasattr(user, 'profile') and not user.profile.is_admin:
            # Regular users can only see their own schedules
            queryset = queryset.filter(created_by=user)
        
        # Filter by active status
        if self.request.query_params.get('active_only') == 'true':
            queryset = queryset.filter(is_active=True)
        
        return queryset.order_by('name')
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ReportExportViewSet(viewsets.ReadOnlyModelViewSet):
    """API ViewSet for report exports (read-only)"""
    serializer_class = ReportExportSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = ReportExport.objects.select_related('report', 'exported_by')
        
        # Filter by user access
        user = self.request.user
        if hasattr(user, 'profile') and not user.profile.is_admin:
            # Regular users can only see their own exports
            queryset = queryset.filter(exported_by=user)
        
        # Filter by format
        format_filter = self.request.query_params.get('format')
        if format_filter:
            queryset = queryset.filter(format=format_filter)
        
        return queryset.order_by('-exported_at')
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download an exported report file"""
        export = self.get_object()
        
        try:
            # Record download
            export.record_download()
            
            # Serve file (implement based on your file storage)
            # This is a placeholder - implement actual file serving
            response = HttpResponse(
                content_type='application/octet-stream'
            )
            response['Content-Disposition'] = f'attachment; filename="{export.file_name}"'
            return response
        
        except Exception as e:
            return Response(
                {'error': f'Download failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# =============================================================================
# Web Views (Template-based)
# =============================================================================

class ReportTemplateListView(LoginRequiredMixin, ListView):
    """List view for report templates"""
    model = ReportTemplate
    template_name = 'reports/template_list.html'
    context_object_name = 'templates'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = ReportTemplate.objects.select_related('created_by')  # type: ignore
        
        # Filter by user access
        user = self.request.user
        if hasattr(user, 'profile'):
            if not user.profile.is_admin:
                queryset = queryset.filter(
                    Q(is_public=True) |
                    Q(allowed_roles__contains=[user.profile.role])
                )
        
        # Filter by type
        report_type = self.request.GET.get('type')
        if report_type:
            queryset = queryset.filter(report_type=report_type)
        
        return queryset.filter(is_active=True).order_by('report_type', 'name')


class ReportTemplateDetailView(LoginRequiredMixin, DetailView):
    """Detail view for report templates"""
    model = ReportTemplate
    template_name = 'reports/template_detail.html'
    context_object_name = 'template'
    
    def get_queryset(self):
        queryset = ReportTemplate.objects.select_related('created_by')  # type: ignore
        
        # Filter by user access
        user = self.request.user
        if hasattr(user, 'profile'):
            if not user.profile.is_admin:
                queryset = queryset.filter(
                    Q(is_public=True) |
                    Q(allowed_roles__contains=[user.profile.role])
                )
        
        return queryset.filter(is_active=True)


class GeneratedReportListView(LoginRequiredMixin, ListView):
    """List view for generated reports"""
    model = GeneratedReport
    template_name = 'reports/report_list.html'
    context_object_name = 'reports'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = GeneratedReport.objects.select_related('template', 'generated_by')  # type: ignore
        
        # Filter out expired reports by default
        show_expired = self.request.GET.get('show_expired', 'false').lower() == 'true'
        if not show_expired:
            queryset = queryset.filter(
                Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
            )
        
        # Filter by user access
        user = self.request.user
        if hasattr(user, 'profile') and not user.profile.is_admin:
            # Regular users can only see their own reports
            queryset = queryset.filter(generated_by=user)
        
        # Filter by template
        template = self.request.GET.get('template')
        if template:
            queryset = queryset.filter(template_id=template)
        
        # Filter by status
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-generated_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['templates'] = ReportTemplate.objects.filter(is_active=True)  # type: ignore
        context['show_expired'] = self.request.GET.get('show_expired', 'false').lower() == 'true'
        return context


class GeneratedReportDetailView(LoginRequiredMixin, DetailView):
    """Detail view for generated reports"""
    model = GeneratedReport
    template_name = 'reports/report_detail.html'
    context_object_name = 'report'
    
    def get_queryset(self):
        queryset = GeneratedReport.objects.select_related('template', 'generated_by')
        
        # Filter by user access
        user = self.request.user
        if hasattr(user, 'profile') and not user.profile.is_admin:
            queryset = queryset.filter(generated_by=user)
        
        return queryset


class GeneratedReportDeleteView(LoginRequiredMixin, DeleteView):
    """Delete view for generated reports"""
    model = GeneratedReport
    template_name = 'reports/report_confirm_delete.html'
    context_object_name = 'report'
    success_url = reverse_lazy('reports:report_list')
    
    def get_queryset(self):
        queryset = GeneratedReport.objects.select_related('template', 'generated_by')
        
        # Filter by user access - only admins or the report creator can delete
        user = self.request.user
        if hasattr(user, 'profile') and not user.profile.is_admin:
            queryset = queryset.filter(generated_by=user)
        
        return queryset
    
    def delete(self, request, *args, **kwargs):
        report = self.get_object()
        report_title = report.title
        
        # Delete associated files if they exist
        exports = report.exports.all()
        for export in exports:
            # Try to delete the file from storage
            try:
                import os
                if os.path.exists(export.file_path):
                    os.remove(export.file_path)
            except Exception:
                # Log error but continue
                pass
        
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f"Report '{report_title}' has been deleted successfully.")
        return response


class ReportGenerateView(LoginRequiredMixin, FormView):
    """Server-side form to generate reports"""
    template_name = 'reports/report_generate.html'
    form_class = ReportGenerationForm

    def get_initial(self):
        initial = super().get_initial()
        template_id = self.request.GET.get('template_id')
        if template_id:
            try:
                template = ReportTemplate.objects.get(id=template_id, is_active=True)
                if template.can_be_accessed_by(self.request.user):
                    initial['template'] = template
            except ReportTemplate.DoesNotExist:
                pass
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        template = form.cleaned_data['template']
        date_from = form.cleaned_data.get('date_from')
        date_to = form.cleaned_data.get('date_to')
        export_format = form.cleaned_data.get('export_format') or None

        # Build dynamic filter parameters from template.config
        parameters = {}
        # Parse config and extract filters list
        config = template.config
        try:
            if isinstance(config, str):
                import json as _json
                config = _json.loads(config)
        except Exception:
            config = {}
        raw_filters = config.get('filters', [])
        filters = raw_filters if isinstance(raw_filters, list) else []
        for f in filters:
            # Ensure each filter is a dict
            if not isinstance(f, dict):
                continue
            name = f.get('name')
            if not name:
                continue
            if f.get('type') == 'date_range':
                parameters[name] = {
                    'from': self.request.POST.get(f"{name}_from"),
                    'to': self.request.POST.get(f"{name}_to"),
                }
            else:
                parameters[name] = self.request.POST.get(name)

        # Generate report with parameters
        service = ReportGenerationService()
        report = service.generate_report(
            template=template,
            user=self.request.user,
            title=None,
            parameters=parameters,
            date_from=date_from,
            date_to=date_to
        )
        # Handle export if requested
        if export_format:
            export_service = ReportExportService()
            return export_service.export_report(report, export_format, self.request.user)

        return redirect('reports:report_detail', pk=report.pk)


# =============================================================================
# AJAX Views
# =============================================================================

@login_required
def report_stats_ajax(request):
    """AJAX endpoint for report statistics"""
    # Get accessible templates
    templates = ReportTemplate.objects.filter(is_active=True)
    user = request.user
    
    if hasattr(user, 'profile') and not user.profile.is_admin:
        templates = templates.filter(
            Q(is_public=True) |
            Q(allowed_roles__contains=[user.profile.role])
        )
    
    # Get generated reports
    reports = GeneratedReport.objects.all()
    if hasattr(user, 'profile') and not user.profile.is_admin:
        reports = reports.filter(generated_by=user)
    
    # Calculate statistics
    total_templates = templates.count()
    total_generated = reports.count()
    completed_reports = reports.filter(status='completed').count()
    failed_reports = reports.filter(status='failed').count()
    
    # Popular templates
    popular_templates = list(
        reports.values('template__name')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )
    
    return JsonResponse({
        'total_templates': total_templates,
        'total_generated': total_generated,
        'completed_reports': completed_reports,
        'failed_reports': failed_reports,
        'popular_templates': popular_templates
    })


@login_required
@login_required
def generate_report_ajax(request):
    """Enhanced AJAX endpoint for generating reports with comprehensive validation"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        template_id = data.get('template_id')
        
        # Validate template ID
        if not template_id:
            return JsonResponse({
                'error': 'Template ID is required',
                'field_errors': {'template_id': 'Please select a report template'}
            }, status=400)
        
        try:
            template = ReportTemplate.objects.get(id=template_id, is_active=True)
        except ReportTemplate.DoesNotExist:
            return JsonResponse({
                'error': 'Selected template not found or inactive',
                'field_errors': {'template_id': 'Selected template is not available'}
            }, status=404)
        
        # Check access permissions
        if not template.can_be_accessed_by(request.user):
            return JsonResponse({
                'error': 'You do not have permission to generate this report type',
                'field_errors': {'template_id': 'Access denied for this template'}
            }, status=403)
        
        # Validate parameters based on report type
        parameters = data.get('parameters', {})
        field_errors = {}
        
        # Enhanced parameter validation
        if template.report_type == 'customer_statement':
            customer_id = parameters.get('customer_id')
            if not customer_id:
                field_errors['customer_id'] = 'Please select a customer for the statement report'
            else:
                try:
                    from customers.models import Customer
                    Customer.objects.get(id=customer_id)
                except Customer.DoesNotExist:
                    field_errors['customer_id'] = 'Selected customer not found'
        
        elif template.report_type == 'expense_summary':
            # Validate required date range for expense reports
            if not data.get('date_from') or not data.get('date_to'):
                field_errors['date_range'] = 'Both start and end dates are required for expense reports'
            
            # Validate expense category if provided
            category_filter = parameters.get('category_filter')
            if category_filter:
                try:
                    from expenses.models import ExpenseCategory
                    ExpenseCategory.objects.get(id=category_filter)
                except ExpenseCategory.DoesNotExist:
                    field_errors['category_filter'] = 'Selected expense category not found'
        
        elif template.report_type == 'service_analysis':
            # Validate service category if provided
            service_category = parameters.get('service_category')
            if service_category:
                try:
                    from services.models import ServiceCategory
                    ServiceCategory.objects.get(id=service_category)
                except ServiceCategory.DoesNotExist:
                    field_errors['service_category'] = 'Selected service category not found'
        
        # Validate date range consistency
        date_from = None
        date_to = None
        
        if data.get('date_from'):
            try:
                date_from = datetime.strptime(data.get('date_from'), '%Y-%m-%d').date()
            except ValueError:
                field_errors['date_from'] = 'Invalid date format. Use YYYY-MM-DD'
                
        if data.get('date_to'):
            try:
                date_to = datetime.strptime(data.get('date_to'), '%Y-%m-%d').date()
            except ValueError:
                field_errors['date_to'] = 'Invalid date format. Use YYYY-MM-DD'
        
        # Check date range logic
        if date_from and date_to and date_from > date_to:
            field_errors['date_range'] = 'Start date cannot be later than end date'
        
        # Check for future dates (optional business rule)
        if date_to and date_to > timezone.now().date():
            field_errors['date_to'] = 'End date cannot be in the future'
        
        # Return validation errors if any
        if field_errors:
            return JsonResponse({
                'error': 'Please correct the following errors:',
                'field_errors': field_errors
            }, status=400)
        
        # Generate report using the service
        service = ReportGenerationService()
        
        try:
            report = service.generate_report(
                template=template,
                title=data.get('title') or f"{template.name} - {timezone.now().strftime('%Y-%m-%d %H:%M')}",
                parameters=parameters,
                date_from=date_from,
                date_to=date_to,
                user=request.user
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Report generated successfully',
                'report': {
                    'id': report.id,
                    'title': report.title,
                    'status': report.status,
                    'template_type': template.get_report_type_display(),
                    'generated_at': report.generated_at.strftime('%Y-%m-%d %H:%M'),
                    'data_size': report.data_size or 0,
                    'url': f"/reports/{report.id}/"
                }
            })
        
        except Exception as generation_error:
            # Log the error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Report generation failed: {generation_error}", exc_info=True)
            
            return JsonResponse({
                'error': 'Failed to generate report. Please try again.',
                'details': str(generation_error) if settings.DEBUG else 'Internal server error'
            }, status=500)
    
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON in request body',
            'field_errors': {'form': 'Invalid request format'}
        }, status=400)
    
    except Exception as e:
        # Log unexpected errors
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Unexpected error in generate_report_ajax: {e}", exc_info=True)
        
        return JsonResponse({
            'error': 'An unexpected error occurred. Please try again.',
            'details': str(e) if settings.DEBUG else 'Internal server error'
        }, status=500)


@login_required
def templates_ajax(request):
    """Simple AJAX endpoint for loading report templates"""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        user = request.user
        print(f"DEBUG: User authenticated: {user.is_authenticated}, User: {user.username}")
        
        # Get templates accessible to the user
        queryset = ReportTemplate.objects.select_related('created_by').filter(is_active=True)
        print(f"DEBUG: Total active templates: {queryset.count()}")
        
        # Filter by user access
        if hasattr(user, 'profile'):
            print(f"DEBUG: User has profile: {user.profile}")
            if not user.profile.is_admin:
                print("DEBUG: User is not admin, filtering templates")
                queryset = queryset.filter(
                    Q(is_public=True) |
                    Q(allowed_roles__contains=[user.profile.role])
                )
        else:
            print("DEBUG: User has no profile, showing public templates only")
            queryset = queryset.filter(is_public=True)
        
        print(f"DEBUG: Accessible templates: {queryset.count()}")
        
        # Convert to list with necessary fields
        templates = []
        for template in queryset.order_by('report_type', 'name'):
            templates.append({
                'id': template.id,
                'name': template.name,
                'report_type': template.report_type,
                'report_type_display': template.get_report_type_display(),
                'description': template.description,
                'is_public': template.is_public
            })
        
        return JsonResponse({
            'success': True,
            'results': templates,
            'count': len(templates)
        })
    
    except Exception as e:
        print(f"DEBUG: Error in templates_ajax: {e}")
        return JsonResponse({
            'error': 'Failed to load templates',
            'details': str(e) if settings.DEBUG else 'Internal server error'
        }, status=500)


from django.template.loader import render_to_string
from django.views.decorators.http import require_GET
from django.db.models import Q
from .models import ReportTemplate  # type: ignore
import json as _json

@require_GET
def filters_ajax(request):
    """AJAX endpoint to return dynamic filter inputs based on template config"""
    template_id = request.GET.get('template_id')
    try:
        tpl = ReportTemplate.objects.get(pk=template_id, is_active=True)  # type: ignore
    except ReportTemplate.DoesNotExist:  # type: ignore
        return JsonResponse({'error': 'Template not found.'}, status=404)

    config = tpl.config or {}
    # Parse config if stored as JSON string
    if isinstance(config, str):
        try:
            config = _json.loads(config)
        except Exception:
            config = {}
    html = render_to_string('reports/partials/_report_filters.html', {'config': config}, request=request)
    return JsonResponse({'html': html})


@login_required
def export_download_view(request, export_id):
    """Direct download view for report exports"""
    try:
        export = get_object_or_404(ReportExport, id=export_id)
        
        # Check if user has permission to download
        if not request.user.is_staff and export.exported_by != request.user:
            raise PermissionDenied("You don't have permission to download this report.")
        
        # Generate and return the file
        service = ReportExportService()
        response = service.export_report(export.report, export.format, request.user)
        
        # Record download
        export.record_download()
        
        return response
        
    except Exception as e:
        return HttpResponse(
            f"Download failed: {str(e)}", 
            status=500, 
            content_type='text/plain'
        )
