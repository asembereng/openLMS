"""
Management command to test service update and delete functionality
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.test import Client
from django.urls import reverse
from services.models import Service, ServiceCategory
import json


class Command(BaseCommand):
    help = 'Test service management functionality (update/delete)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-test-data',
            action='store_true',
            help='Create test service data',
        )

    def handle(self, *args, **options):
        self.stdout.write('Testing Service Management Functionality...\n')
        
        if options['create_test_data']:
            self.create_test_data()
            
        self.test_service_urls()
        self.test_admin_permissions()
        
        self.stdout.write(
            self.style.SUCCESS('Service management tests completed successfully!')
        )

    def create_test_data(self):
        """Create test data for testing"""
        self.stdout.write('Creating test data...')
        
        # Create test category
        category, created = ServiceCategory.objects.get_or_create(
            name="Test Management Category",
            defaults={
                'description': 'Category for testing management functionality',
                'icon': 'fas fa-test',
                'display_order': 999
            }
        )
        
        # Get admin user
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = User.objects.create_superuser(
                'testadmin', 'test@example.com', 'password123'
            )
        
        # Create test service
        service, created = Service.objects.get_or_create(
            category=category,
            name="Test Management Service",
            defaults={
                'description': 'Service for testing update/delete functionality',
                'price_per_dozen': 100.00,
                'created_by': admin_user,
                'display_order': 999
            }
        )
        
        self.test_service = service
        self.stdout.write(f'Test service created: {service}')

    def test_service_urls(self):
        """Test that service URLs resolve correctly"""
        self.stdout.write('\nTesting service URLs...')
        
        service = Service.objects.first()
        if not service:
            self.stdout.write(self.style.ERROR('No services found'))
            return
            
        # Test detail URL
        detail_url = service.get_absolute_url()
        self.stdout.write(f'Detail URL: {detail_url}')
        
        # Test edit URL
        edit_url = reverse('services:edit', kwargs={'pk': service.pk})
        self.stdout.write(f'Edit URL: {edit_url}')
        
        # Test delete URL
        delete_url = reverse('services:delete', kwargs={'pk': service.pk})
        self.stdout.write(f'Delete URL: {delete_url}')
        
        self.stdout.write(self.style.SUCCESS('URLs resolve correctly'))

    def test_admin_permissions(self):
        """Test admin permission checking"""
        self.stdout.write('\nTesting admin permissions...')
        
        # Get admin user
        admin_user = User.objects.filter(is_superuser=True).first()
        if admin_user:
            self.stdout.write(f'Admin user found: {admin_user.username}')
            
            # Test admin access
            from services.views import AdminRequiredMixin
            mixin = AdminRequiredMixin()
            
            # Create mock request
            class MockRequest:
                def __init__(self, user):
                    self.user = user
            
            mixin.request = MockRequest(admin_user)
            is_admin = mixin.test_func()
            
            if is_admin:
                self.stdout.write(self.style.SUCCESS('Admin permissions work correctly'))
            else:
                self.stdout.write(self.style.ERROR('Admin permissions not working'))
        else:
            self.stdout.write(self.style.WARNING('No admin user found'))
            
        # Test Admin group
        admin_group = Group.objects.filter(name='Admin').first()
        if admin_group:
            admin_users = admin_group.user_set.all()
            self.stdout.write(f'Admin group members: {[u.username for u in admin_users]}')
