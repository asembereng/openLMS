from django.urls import path
from . import views

app_name = 'loyalty'

urlpatterns = [
    path('', views.LoyaltyAccountListView.as_view(), name='dashboard'),
    path('rules/', views.LoyaltyRuleListView.as_view(), name='rule_list'),
    path('rules/select-template/', views.LoyaltyRuleTemplateSelectionView.as_view(), name='rule_select_template'),
    path('rules/new/', views.LoyaltyRuleCreateView.as_view(), name='rule_create'),
    path('rules/<int:pk>/edit/', views.LoyaltyRuleUpdateView.as_view(), name='rule_update'),
    path('rules/<int:pk>/delete/', views.LoyaltyRuleDeleteView.as_view(), name='rule_delete'),
]
