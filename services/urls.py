"""
Services app URL configuration
"""
from django.urls import path
from . import views

app_name = 'services'

urlpatterns = [
    # Service Category URLs
    path('categories/', views.ServiceCategoryListView.as_view(), name='category_list'),
    path('categories/create/', views.ServiceCategoryCreateView.as_view(), name='category_create'),
    path('categories/<int:pk>/edit/', views.ServiceCategoryUpdateView.as_view(), name='category_edit'),
    
    # Service URLs
    path('', views.ServiceListView.as_view(), name='list'),
    path('create/', views.ServiceCreateView.as_view(), name='create'),
    path('<int:pk>/', views.ServiceDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.ServiceUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.ServiceDeleteView.as_view(), name='delete'),
    
    # AJAX endpoints
    path('search/', views.service_search_ajax, name='search_ajax'),
    
    # API endpoints - Categories
    path('api/categories/', views.ServiceCategoryListCreateAPIView.as_view(), name='api_category_list_create'),
    path('api/categories/<int:pk>/', views.ServiceCategoryRetrieveUpdateAPIView.as_view(), name='api_category_detail'),
    
    # API endpoints - Services
    path('api/', views.ServiceListCreateAPIView.as_view(), name='api_list_create'),
    path('api/<int:pk>/', views.ServiceRetrieveUpdateAPIView.as_view(), name='api_detail'),
    path('api/by-category/', views.services_by_category_api, name='api_by_category'),
    path('api/stats/', views.service_stats_api, name='api_stats'),
]
