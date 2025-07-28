from django.db import models
from django.utils import timezone
from customers.models import Customer
from orders.models import Order

class LoyaltyAccount(models.Model):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE)
    points_balance = models.IntegerField(default=0)
    tier = models.CharField(max_length=20, default="Standard")
    tier_expiry = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"LoyaltyAccount({self.customer.name}, Points: {self.points_balance}, Tier: {self.tier})"

class LoyaltyTransaction(models.Model):
    account = models.ForeignKey(LoyaltyAccount, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.SET_NULL)
    points_change = models.IntegerField()
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transaction({self.account.customer.name}, Points: {self.points_change})"

class LoyaltyRule(models.Model):
    """
    Defines a rule for earning loyalty points or rewards.
    e.g., "Earn 1 point for every $10 spent" or "Get 100 bonus points on your 5th order."
    """
    TRIGGER_TYPE_CHOICES = [
        ('SPEND_BASED', 'Spend-Based'),
        ('ORDER_FREQUENCY', 'Order Frequency'),
        ('FIRST_ORDER', 'First Order'),
        ('REFERRAL', 'Referral'),
        ('BIRTHDAY_BONUS', 'Birthday Bonus'),
        ('MANUAL_ADJUSTMENT', 'Manual Adjustment'),
    ]

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    trigger_type = models.CharField(
        max_length=50,
        choices=TRIGGER_TYPE_CHOICES,
        help_text="The event that triggers this rule."
    )
    config = models.JSONField(
        default=dict,
        help_text="JSON configuration for the trigger (e.g., {\"threshold\": 100})"
    )
    reward = models.JSONField(
        default=dict,
        help_text="JSON configuration for the reward (e.g., {\"type\": \"POINTS\", \"amount\": 10})"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Rule({self.name}, Type: {self.trigger_type})"

class Referral(models.Model):
    code = models.CharField(max_length=8, unique=True)
    referrer = models.ForeignKey(Customer, related_name="sent_referrals", on_delete=models.CASCADE)
    referee = models.ForeignKey(Customer, related_name="received_referral", on_delete=models.CASCADE)
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.SET_NULL)
    reward_granted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Referral({self.referrer.name} → {self.referee.name})"
