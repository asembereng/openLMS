"""
Management command to create a test user and send welcome email
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
from accounts.models import UserProfile
from accounts.email_service import UserEmailService


class Command(BaseCommand):
    help = 'Create a test user and send welcome email'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='testuser_' + get_random_string(5).lower(),
            help='Username for the test user',
        )
        parser.add_argument(
            '--email',
            type=str,
            required=True,
            help='Email address for the test user',
        )
        parser.add_argument(
            '--first-name',
            type=str,
            default='Test',
            help='First name for the test user',
        )
        parser.add_argument(
            '--last-name',
            type=str,
            default='User',
            help='Last name for the test user',
        )
        parser.add_argument(
            '--role',
            type=str,
            choices=['admin', 'normal_user'],
            default='normal_user',
            help='Role for the test user',
        )

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        first_name = options['first_name']
        last_name = options['last_name']
        role = options['role']
        
        # Check if user already exists
        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.ERROR(f'User with username "{username}" already exists')
            )
            return
        
        if User.objects.filter(email=email).exists():
            self.stdout.write(
                self.style.ERROR(f'User with email "{email}" already exists')
            )
            return
        
        # Generate random password
        password = get_random_string(12)
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password
        )
        
        # Create user profile
        UserProfile.objects.create(
            user=user,
            role=role
        )
        
        # Get admin user for created_by
        admin_user = User.objects.filter(is_superuser=True).first()
        
        self.stdout.write(f'Created user: {username}')
        self.stdout.write(f'Email: {email}')
        self.stdout.write(f'Password: {password}')
        self.stdout.write(f'Role: {role}')
        
        # Send welcome email
        self.stdout.write('\\nSending welcome email...')
        email_sent = UserEmailService.send_welcome_email(
            user=user,
            password=password,
            created_by=admin_user
        )
        
        if email_sent:
            self.stdout.write(
                self.style.SUCCESS(f'✅ Welcome email sent successfully to {email}!')
            )
        else:
            self.stdout.write(
                self.style.ERROR(f'❌ Failed to send welcome email to {email}')
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'\\n🎉 Test user "{username}" created successfully!')
        )
