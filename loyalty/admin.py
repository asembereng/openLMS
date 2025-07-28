from django.contrib import admin
from loyalty.models import LoyaltyAccount, LoyaltyTransaction, LoyaltyRule, Referral

@admin.register(LoyaltyAccount)
class LoyaltyAccountAdmin(admin.ModelAdmin):
    list_display = ('customer', 'points_balance', 'tier', 'tier_expiry')
    search_fields = ('customer__name', 'tier')

@admin.register(LoyaltyTransaction)
class LoyaltyTransactionAdmin(admin.ModelAdmin):
    list_display = ('account', 'order', 'points_change', 'description', 'created_at')
    search_fields = ('account__customer__name', 'description')
    list_filter = ('created_at',)

@admin.register(LoyaltyRule)
class LoyaltyRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'trigger_type', 'is_active', 'created_at', 'updated_at')
    search_fields = ('name', 'trigger_type')
    list_filter = ('is_active', 'trigger_type')

@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ('code', 'referrer', 'referee', 'reward_granted', 'created_at')
    search_fields = ('code', 'referrer__name', 'referee__name')
    list_filter = ('reward_granted', 'created_at')
