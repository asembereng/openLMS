from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction

User = get_user_model()

class Command(BaseCommand):
    help = 'Create admin user and Admin group'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='Admin email address', required=True)
        parser.add_argument('--password', type=str, help='Admin password')
        parser.add_argument('--first-name', type=str, help='Admin first name')
        parser.add_argument('--last-name', type=str, help='Admin last name')

    def handle(self, *args, **options):
        email = options['email']
        password = options.get('password')
        first_name = options.get('first_name', '')
        last_name = options.get('last_name', '')

        with transaction.atomic():
            # Create Admin group if it doesn't exist
            admin_group, created = Group.objects.get_or_create(name='Admin')
            if created:
                self.stdout.write('Created Admin group')
            else:
                self.stdout.write('Admin group already exists')

            # Check if user exists
            if User.objects.filter(email=email).exists():
                self.stdout.write(f'User with email {email} already exists')
                return

            # Create admin user
            if not password:
                password = input(f'Enter password for {email}: ')

            # Generate username from email
            username = email.split('@')[0]
            
            # Ensure username is unique
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_staff=True  # Allow access to Django admin
            )

            # Add user to Admin group
            user.groups.add(admin_group)

            self.stdout.write(f'Successfully created admin user: {email}')
            self.stdout.write('  - Added to Admin group')
            self.stdout.write('  - Has staff access to Django admin')
            
            # Display user permissions
            self.stdout.write('\nAdmin user can now:')
            self.stdout.write('  - Create, edit, and delete services')
            self.stdout.write('  - Create, edit, and delete service categories')
            self.stdout.write('  - Access all admin-only features')
            self.stdout.write('  - Access Django admin interface')
