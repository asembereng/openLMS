from django.core.management.base import BaseCommand
from reports.models import ReportTemplate


class Command(BaseCommand):
    help = 'List all available report templates'

    def handle(self, *args, **options):
        templates = ReportTemplate.objects.filter(is_active=True).order_by('report_type', 'name')
        
        if not templates.exists():
            self.stdout.write(
                self.style.WARNING('No report templates found. Run: python manage.py seed_report_templates')
            )
            return

        self.stdout.write(self.style.SUCCESS(f'Found {templates.count()} report templates:\n'))
        
        current_type = None
        for template in templates:
            if template.report_type != current_type:
                current_type = template.report_type
                self.stdout.write(f'\n{template.get_report_type_display()}:')
                self.stdout.write('-' * 40)
            
            access = 'Public' if template.is_public else f'Roles: {", ".join(template.allowed_roles)}'
            self.stdout.write(f'  • {template.name}')
            self.stdout.write(f'    {template.description}')
            self.stdout.write(f'    Access: {access}')
            self.stdout.write('')
        
        self.stdout.write(
            self.style.SUCCESS(
                'Visit http://127.0.0.1:8000/reports/templates/ to manage these templates.'
            )
        )
