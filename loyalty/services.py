from loyalty.models import LoyaltyAccount, LoyaltyTransaction, LoyaltyRule, Referral
from orders.models import Order
from django.utils.timezone import now
from datetime import timedelta
from django.db import models
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError

def evaluate_loyalty_rules(order):
    """Evaluate active loyalty rules for a given order."""
    customer = order.customer
    account, _ = LoyaltyAccount.objects.get_or_create(customer=customer)

    active_rules = LoyaltyRule.objects.filter(is_active=True)

    for rule in active_rules:
        if rule.trigger_type == 'ORDER_COUNT':
            threshold = rule.config.get('threshold', 0)
            if customer.orders.count() >= threshold:
                apply_reward(account, rule.reward, order)

        elif rule.trigger_type == 'FREQUENCY':
            n_orders = rule.config.get('n_orders', 0)
            n_days = rule.config.get('n_days', 0)
            start_date = now() - timedelta(days=n_days)
            recent_orders = customer.orders.filter(created_at__gte=start_date).count()
            if recent_orders >= n_orders:
                apply_reward(account, rule.reward, order)

        elif rule.trigger_type == 'SPEND':
            amount = rule.config.get('amount', 0)
            window_days = rule.config.get('window_days', 0)
            if window_days > 0:
                start_date = now() - timedelta(days=window_days)
                total_spent = customer.orders.filter(created_at__gte=start_date).aggregate(total=models.Sum('total_amount'))['total'] or 0
            else:
                total_spent = customer.total_spent
            if total_spent >= amount:
                apply_reward(account, rule.reward, order)

        elif rule.trigger_type == 'REFERRAL':
            referral = Referral.objects.filter(referee=customer, reward_granted=False).first()
            if referral and order.total_amount >= rule.config.get('minimum_order_value', 0):
                apply_reward(account, rule.reward, order)
                referral.reward_granted = True
                referral.save()

def apply_reward(account, reward, order):
    """Apply a reward to a loyalty account."""
    if reward['type'] == 'POINTS':
        points = reward.get('amount', 0)
        account.points_balance += points
        account.save()
        LoyaltyTransaction.objects.create(
            account=account,
            order=order,
            points_change=points,
            description=f"Points reward: {points} points"
        )
    # Additional reward types (e.g., coupons, free services) can be implemented here.


def redeem_points(order: Order, points_to_redeem: int):
    """
    Redeems loyalty points for a discount on a given order.

    Args:
        order (Order): The order to apply the discount to.
        points_to_redeem (int): The number of points to redeem.

    Returns:
        tuple[bool, str]: A tuple containing a boolean indicating success
                         and a message.

    Raises:
        ValidationError: If the redemption is not possible for various reasons.
    """
    if not isinstance(points_to_redeem, int) or points_to_redeem <= 0:
        raise ValidationError("Points to redeem must be a positive integer.")

    try:
        account = order.customer.loyalty_account
    except LoyaltyAccount.DoesNotExist:
        raise ValidationError("Customer does not have a loyalty account.")

    if account.points_balance < points_to_redeem:
        raise ValidationError(f"Insufficient loyalty points. Available: {account.points_balance}")

    # Calculate redemption value based on the rate in settings
    redemption_rate = getattr(settings, 'LOYALTY_POINTS_REDEMPTION_RATE', Decimal('0.10'))
    discount_amount = (Decimal(points_to_redeem) * redemption_rate).quantize(
        Decimal('0.01'), rounding='ROUND_HALF_UP'
    )

    # Ensure discount doesn't exceed the current order total
    # We use the subtotal here to avoid issues with other discounts
    current_order_total = order.subtotal - order.discount_amount
    if discount_amount > current_order_total:
        # Calculate max points that can be redeemed
        max_redeemable_points = int(current_order_total / redemption_rate)
        raise ValidationError(
            f"Discount ({settings.CURRENCY_SYMBOL}{discount_amount}) exceeds order total. "
            f"You can redeem a maximum of {max_redeemable_points} points on this order."
        )

    # Apply redemption to the order
    order.loyalty_discount_amount = discount_amount
    order.redeemed_points = points_to_redeem
    order.save() # This will trigger calculate_totals via the save method

    # Update loyalty account and create a transaction log
    account.points_balance -= points_to_redeem
    account.save()

    LoyaltyTransaction.objects.create(
        account=account,
        order=order,
        points_change=-points_to_redeem,
        description=f"Redeemed {points_to_redeem} points for a {settings.CURRENCY_SYMBOL}{discount_amount} discount."
    )

    return True, f"Successfully redeemed {points_to_redeem} points for a {settings.CURRENCY_SYMBOL}{discount_amount} discount."
