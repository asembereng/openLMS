"""
Customers app URL configuration
"""
from django.urls import path
from . import views

app_name = 'customers'

urlpatterns = [
    # Web views
    path('', views.CustomerListView.as_view(), name='list'),
    path('create/', views.CustomerCreateView.as_view(), name='create'),
    path('<int:pk>/', views.CustomerDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.CustomerUpdateView.as_view(), name='edit'),
    
    # AJAX endpoints
    path('search/', views.customer_search_ajax, name='search_ajax'),
    
    # API endpoints
    path('api/', views.CustomerListCreateAPIView.as_view(), name='api_list_create'),
    path('api/<int:pk>/', views.CustomerRetrieveUpdateAPIView.as_view(), name='api_detail'),
    path('api/stats/', views.customer_stats_api, name='api_stats'),
]
