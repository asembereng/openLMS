from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Create a default superuser if none exists'

    def handle(self, *args, **options):
        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@openlms.com',
                password='admin123'
            )
            self.stdout.write(
                self.style.SUCCESS('Default superuser created: admin/admin123')
            )
        else:
            self.stdout.write(
                self.style.WARNING('Superuser already exists')
            )
