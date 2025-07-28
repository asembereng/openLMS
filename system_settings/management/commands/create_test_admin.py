"""
Management command to create a test admin user for testing admin settings
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import UserProfile


class Command(BaseCommand):
    help = 'Create a test admin user for testing admin settings functionality'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='testadmin',
            help='Username for the admin user',
        )
        parser.add_argument(
            '--email',
            type=str,
            default='admin@test.com',
            help='Email for the admin user',
        )
        parser.add_argument(
            '--password',
            type=str,
            default='testpass123',
            help='Password for the admin user',
        )

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']
        
        # Check if user already exists
        if User.objects.filter(username=username).exists():
            self.stdout.write(f'User {username} already exists.')
            user = User.objects.get(username=username)
        else:
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name='Test',
                last_name='Admin',
                is_staff=True,
                is_superuser=True
            )
            self.stdout.write(f'Created user: {username}')
        
        # Ensure user has a profile and is admin
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if profile.role != 'admin':
            profile.role = 'admin'
            profile.save()
            self.stdout.write(f'Made {username} an admin user')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Admin user ready!\n'
                f'Username: {username}\n'
                f'Password: {password}\n'
                f'You can now test the admin settings at /admin-settings/'
            )
        )
