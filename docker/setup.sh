#!/bin/bash
set -e

# Wait for a moment to ensure the system is ready
sleep 2

echo "Starting Django setup..."

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Create superuser if it doesn't exist
echo "Creating superuser..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='admin@openlms.com').exists():
    User.objects.create_superuser(
        username='admin',
        email='admin@openlms.com',
        password='admin123',
        first_name='System',
        last_name='Administrator'
    )
    print('Superuser created: admin@openlms.com / admin123')
else:
    print('Superuser already exists')
"

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Load initial data if needed
echo "Loading initial data..."
python manage.py shell -c "
from system_settings.models import SystemSetting
from django.core.exceptions import ObjectDoesNotExist

# Create default system settings
defaults = [
    ('COMPANY_NAME', 'A&F Laundry Services'),
    ('COMPANY_ADDRESS', '123 Laundry Street, Lagos, Nigeria'),
    ('COMPANY_PHONE', '+234-800-LAUNDRY'),
    ('COMPANY_EMAIL', 'info@aflaundry.com'),
    ('CURRENCY_SYMBOL', '₦'),
    ('TIMEZONE', 'Africa/Lagos'),
    ('PIECES_PER_DOZEN', '12'),
    ('DEFAULT_TAX_RATE', '0.00'),
]

for key, value in defaults:
    setting, created = SystemSetting.objects.get_or_create(
        key=key,
        defaults={'value': value}
    )
    if created:
        print(f'Created setting: {key} = {value}')
"

echo "Django setup completed successfully!"
