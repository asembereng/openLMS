from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models import Q

User = get_user_model()

class Command(BaseCommand):
    help = 'List users and their admin permissions'

    def handle(self, *args, **options):
        admin_group = Group.objects.filter(name='Admin').first()
        
        self.stdout.write('=== USER PERMISSIONS ===\n')
        
        # List superusers
        superusers = User.objects.filter(is_superuser=True)
        if superusers.exists():
            self.stdout.write('SUPERUSERS (Full Admin Access):')
            for user in superusers:
                self.stdout.write(f'  - {user.email} ({user.get_full_name()})')
            self.stdout.write('')
        
        # List Admin group members
        if admin_group:
            admin_users = admin_group.user_set.all()
            if admin_users.exists():
                self.stdout.write('ADMIN GROUP MEMBERS (Services Admin Access):')
                for user in admin_users:
                    status = ' (Superuser)' if user.is_superuser else ''
                    self.stdout.write(f'  - {user.email} ({user.get_full_name()}){status}')
                self.stdout.write('')
        
        # List regular users
        if admin_group:
            regular_users = User.objects.exclude(
                is_superuser=True
            ).exclude(
                groups=admin_group
            )
        else:
            regular_users = User.objects.filter(is_superuser=False)
            
        if regular_users.exists():
            self.stdout.write('REGULAR USERS (View-Only Access):')
            for user in regular_users:
                self.stdout.write(f'  - {user.email} ({user.get_full_name()})')
            self.stdout.write('')
        
        # Summary
        total_users = User.objects.count()
        admin_count = User.objects.filter(
            Q(is_superuser=True) | Q(groups__name='Admin')
        ).distinct().count()
        
        self.stdout.write('=== SUMMARY ===')
        self.stdout.write(f'Total Users: {total_users}')
        self.stdout.write(f'Admin Users: {admin_count}')
        self.stdout.write(f'Regular Users: {total_users - admin_count}')
        
        if not admin_group:
            self.stdout.write('\nWARNING: Admin group does not exist. Create it with:')
            self.stdout.write('  python manage.py create_admin --email admin@example.com')
