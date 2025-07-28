from django.db.models.signals import post_save
from django.dispatch import receiver
from orders.models import Order
from loyalty.services import evaluate_loyalty_rules

@receiver(post_save, sender=Order)
def handle_order_save(sender, instance, created, **kwargs):
    """Evaluate loyalty rules when an order is saved."""
    if created and instance.status in ['completed', 'delivered']:
        evaluate_loyalty_rules(instance)
