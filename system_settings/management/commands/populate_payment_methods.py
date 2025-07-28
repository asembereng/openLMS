"""
Management command to populate default payment methods
"""

from django.core.management.base import BaseCommand
from system_settings.models import PaymentMethod


class Command(BaseCommand):
    help = 'Populate default payment methods'

    def handle(self, *args, **options):
        """Create default payment methods"""
        
        default_payment_methods = [
            {
                'code': 'cash',
                'name': 'Cash Payment',
                'description': 'Payment made with physical cash',
                'icon': 'fa-money-bill',
                'sort_order': 1,
                'is_active': True,
                'requires_verification': False,
            },
            {
                'code': 'card',
                'name': 'Credit/Debit Card',
                'description': 'Payment made with credit or debit card',
                'icon': 'fa-credit-card',
                'sort_order': 2,
                'is_active': True,
                'requires_verification': False,
            },
            {
                'code': 'mobile_money',
                'name': 'Mobile Money',
                'description': 'Payment made through mobile money services',
                'icon': 'fa-mobile-alt',
                'sort_order': 3,
                'is_active': True,
                'requires_verification': False,
            },
            {
                'code': 'bank_transfer',
                'name': 'Bank Transfer',
                'description': 'Direct bank to bank transfer',
                'icon': 'fa-university',
                'sort_order': 4,
                'is_active': True,
                'requires_verification': True,
            },
            {
                'code': 'credit',
                'name': 'Credit (Pay Later)',
                'description': 'Customer will pay at a later date',
                'icon': 'fa-handshake',
                'sort_order': 5,
                'is_active': True,
                'requires_verification': False,
            },
        ]
        
        created_count = 0
        for payment_data in default_payment_methods:
            payment_method, created = PaymentMethod.objects.get_or_create(
                code=payment_data['code'],
                defaults=payment_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created payment method: {payment_method.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Payment method already exists: {payment_method.name}')
                )
        
        if created_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created {created_count} payment methods')
            )
        else:
            self.stdout.write(
                self.style.WARNING('No new payment methods were created')
            )
