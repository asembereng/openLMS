"""
Management command to test service frontend functionality
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.test import RequestFactory
from services.models import Service


class Command(BaseCommand):
    help = 'Test service frontend templates and functionality'

    def handle(self, *args, **options):
        self.stdout.write('Testing Service Frontend Functionality...\n')
        
        # Test 1: Check if admin user exists and has proper permissions
        self.test_admin_permissions()
        
        # Test 2: Test template rendering with admin user
        self.test_template_rendering()
        
        # Test 3: Check service model and URLs
        self.test_service_urls()
        
        self.stdout.write(
            self.style.SUCCESS('\nService frontend tests completed!')
        )

    def test_admin_permissions(self):
        """Test admin user permissions"""
        self.stdout.write('1. Testing admin permissions...')
        
        admin_users = User.objects.filter(is_superuser=True)
        admin_group_users = User.objects.filter(groups__name='Admin')
        
        self.stdout.write(f'   - Superusers: {admin_users.count()}')
        self.stdout.write(f'   - Admin group users: {admin_group_users.count()}')
        
        if admin_users.exists():
            admin_user = admin_users.first()
            self.stdout.write(f'   - Test admin: {admin_user.username}')
            
            # Test admin filter
            from services.templatetags.admin_tags import is_admin
            admin_status = is_admin(admin_user)
            self.stdout.write(f'   - is_admin filter result: {admin_status}')
            
            if admin_status:
                self.stdout.write('   ✓ Admin permissions working correctly')
            else:
                self.stdout.write('   ✗ Admin permissions not working')
        else:
            self.stdout.write('   ✗ No admin users found')

    def test_template_rendering(self):
        """Test template rendering with admin context"""
        self.stdout.write('\n2. Testing template rendering...')
        
        # Get admin user and service
        admin_user = User.objects.filter(is_superuser=True).first()
        service = Service.objects.first()
        
        if admin_user and service:
            # Create mock request
            factory = RequestFactory()
            request = factory.get(f'/services/{service.pk}/')
            request.user = admin_user
            
            try:
                # Test service detail template
                from django.template import Context, Template
                from django.template.loader import get_template
                
                template = get_template('services/service_detail.html')
                context = {
                    'service': service,
                    'user': admin_user,
                    'request': request
                }
                
                rendered = template.render(context)
                
                # Check for admin buttons
                has_edit_button = 'Edit Service' in rendered
                has_delete_button = 'Delete Service' in rendered
                
                self.stdout.write(f'   - Template renders: ✓')
                self.stdout.write(f'   - Edit button present: {has_edit_button}')
                self.stdout.write(f'   - Delete button present: {has_delete_button}')
                
                if has_edit_button and has_delete_button:
                    self.stdout.write('   ✓ Admin buttons rendered correctly')
                else:
                    self.stdout.write('   ✗ Admin buttons missing from template')
                    
            except Exception as e:
                self.stdout.write(f'   ✗ Template rendering error: {e}')
        else:
            self.stdout.write('   ✗ Missing admin user or service for testing')

    def test_service_urls(self):
        """Test service URL generation"""
        self.stdout.write('\n3. Testing service URLs...')
        
        service = Service.objects.first()
        if service:
            from django.urls import reverse
            
            try:
                detail_url = reverse('services:detail', kwargs={'pk': service.pk})
                edit_url = reverse('services:edit', kwargs={'pk': service.pk})
                delete_url = reverse('services:delete', kwargs={'pk': service.pk})
                
                self.stdout.write(f'   - Detail URL: {detail_url}')
                self.stdout.write(f'   - Edit URL: {edit_url}')
                self.stdout.write(f'   - Delete URL: {delete_url}')
                self.stdout.write('   ✓ All URLs resolve correctly')
                
            except Exception as e:
                self.stdout.write(f'   ✗ URL resolution error: {e}')
        else:
            self.stdout.write('   ✗ No services found for URL testing')
