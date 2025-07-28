"""
Reports app URL configuration
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import ReportGenerateView, export_download_view  # add import

# DRF Router for API endpoints
router = DefaultRouter()
router.register(r'templates', views.ReportTemplateViewSet, basename='template')
router.register(r'generated', views.GeneratedReportViewSet, basename='generated-report')
router.register(r'schedules', views.ReportScheduleViewSet, basename='schedule')
router.register(r'exports', views.ReportExportViewSet, basename='export')

app_name = 'reports'

urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
    
    # Web views - Templates
    path('templates/', views.ReportTemplateListView.as_view(), name='template_list'),
    path('templates/<int:pk>/', views.ReportTemplateDetailView.as_view(), name='template_detail'),
    
    # Web views - Generated Reports
    path('', views.GeneratedReportListView.as_view(), name='report_list'),
    path('<int:pk>/', views.GeneratedReportDetailView.as_view(), name='report_detail'),
    path('<int:pk>/delete/', views.GeneratedReportDeleteView.as_view(), name='report_delete'),
    
    # Export downloads
    path('export/<int:export_id>/download/', views.export_download_view, name='export_download'),
    
    # Server-side report generate form
    path('generate/', ReportGenerateView.as_view(), name='report_generate'),

    # AJAX endpoints
    path('ajax/stats/', views.report_stats_ajax, name='stats_ajax'),
    path('ajax/generate/', views.generate_report_ajax, name='generate_ajax'),
    path('ajax/templates/', views.templates_ajax, name='templates_ajax'),
    path('ajax/filters/', views.filters_ajax, name='filters_ajax'),
]
