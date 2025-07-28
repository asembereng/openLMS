"""
Expenses app URL configuration
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# DRF Router for API endpoints
router = DefaultRouter()
router.register(r'categories', views.ExpenseCategoryViewSet)
router.register(r'expenses', views.ExpenseViewSet, basename='expense')
router.register(r'attachments', views.ExpenseAttachmentViewSet, basename='attachment')
router.register(r'approval-requests', views.ExpenseApprovalRequestViewSet, basename='approval-request')

app_name = 'expenses'

urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
    
    # Web views
    path('', views.ExpenseListView.as_view(), name='list'),
    path('<int:pk>/', views.ExpenseDetailView.as_view(), name='detail'),
    path('create/', views.ExpenseCreateView.as_view(), name='create'),
    path('<int:pk>/edit/', views.ExpenseUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.ExpenseDeleteView.as_view(), name='delete'),
    
    # AJAX endpoints
    path('ajax/stats/', views.expense_stats_ajax, name='stats_ajax'),
    path('ajax/search/', views.expense_search_ajax, name='search_ajax'),
    path('ajax/<int:pk>/approve/', views.approve_expense_ajax, name='approve_ajax'),
]
