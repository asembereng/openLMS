from django.test import TestCase
from customers.models import Customer
from orders.models import Order
from loyalty.models import LoyaltyAccount, LoyaltyRule, Referral
from loyalty.services import evaluate_loyalty_rules
from datetime import timedelta
from django.utils.timezone import now
from django.contrib.auth.models import User
from system_settings.models import PaymentMethod

class LoyaltyModuleTests(TestCase):

    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(username="testuser", password="password")

        # Create test customers
        self.customer1 = Customer.objects.create(name="John Doe", phone="123456789", created_by=self.user)
        self.customer2 = Customer.objects.create(name="Jane Smith", phone="987654321", created_by=self.user)

        # Create loyalty account for customer1
        self.account1 = LoyaltyAccount.objects.create(customer=self.customer1, points_balance=0)

        # Create a test payment method
        self.payment_method = PaymentMethod.objects.create(code="cash", name="Cash")

        # Create test orders
        self.order1 = Order.objects.create(customer=self.customer1, total_amount=500, status='completed', created_by=self.user, payment_method=self.payment_method)
        self.order2 = Order.objects.create(customer=self.customer1, total_amount=1000, status='completed', created_by=self.user, payment_method=self.payment_method)

        # Create a referral
        self.referral = Referral.objects.create(referrer=self.customer1, referee=self.customer2, code="REF12345")

        # Create loyalty rules
        self.rule_order_count = LoyaltyRule.objects.create(
            name="5th Order Reward",
            trigger_type="ORDER_COUNT",
            config={"threshold": 5},
            reward={"type": "POINTS", "amount": 100},
            is_active=True
        )

        self.rule_spend = LoyaltyRule.objects.create(
            name="Spend Reward",
            trigger_type="SPEND",
            config={"amount": 1000, "window_days": 0},
            reward={"type": "POINTS", "amount": 50},
            is_active=True
        )

    def test_loyalty_account_creation(self):
        """Test that a loyalty account is created for a customer."""
        self.assertEqual(self.account1.points_balance, 0)

    def test_evaluate_loyalty_rules_order_count(self):
        """Test that the order count rule is evaluated correctly."""
        evaluate_loyalty_rules(self.order1)
        self.account1.refresh_from_db()
        self.assertEqual(self.account1.points_balance, 0)  # Not yet 5 orders

    def test_evaluate_loyalty_rules_spend(self):
        """Test that the spend rule is evaluated correctly."""
        evaluate_loyalty_rules(self.order2)
        self.account1.refresh_from_db()
        self.assertEqual(self.account1.points_balance, 50)  # 1000 spend reward

    def test_referral_reward(self):
        """Test that a referral reward is granted correctly."""
        self.order3 = Order.objects.create(customer=self.customer2, total_amount=300, status='completed')
        evaluate_loyalty_rules(self.order3)
        self.account1.refresh_from_db()
        self.assertEqual(self.account1.points_balance, 50)  # Referral reward
