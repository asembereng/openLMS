"""
Orders app URL configuration
"""
from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # Web Views
    path('', views.OrderListView.as_view(), name='list'),
    path('<int:pk>/', views.OrderDetailView.as_view(), name='detail'),
    path('pos/', views.POSView.as_view(), name='create'),  # Mobile-first POS with workflow
    path('pos/desktop/', views.DesktopPOSView.as_view(), name='create_desktop'),  # Desktop-only POS
    path('<int:pk>/receipt/', views.generate_receipt, name='receipt'),
    path('<int:pk>/receipt/pdf/', views.generate_receipt_pdf, name='receipt_pdf'),
    path('<int:pk>/receipt/png/', views.download_receipt_png, name='receipt_png'),
    path('<int:pk>/whatsapp/validate/', views.validate_whatsapp_number, name='whatsapp_validate'),
    path('<int:pk>/whatsapp/share/', views.generate_whatsapp_share, name='whatsapp_share'),
    path('<int:pk>/whatsapp/share-with-attachment/', views.generate_whatsapp_share_with_attachment, name='whatsapp_share_attachment'),
    path('<int:pk>/update-status/', views.update_order_status, name='update_status'),
    path('api/customer-points/', views.get_customer_loyalty_points, name='api_customer_points'),
    
    # API endpoints
    path('api/', views.OrderListCreateAPIView.as_view(), name='api_list_create'),
    path('api/<int:pk>/', views.OrderRetrieveUpdateAPIView.as_view(), name='api_detail'),
    path('api/<int:pk>/status/', views.OrderUpdateStatusAPIView.as_view(), name='api_update_status'),
    path('api/stats/', views.order_stats_api, name='api_stats'),
    path('api/recent/', views.recent_orders_api, name='api_recent'),
    path('api/quick-create/', views.quick_order_api, name='api_quick_create'),
]
