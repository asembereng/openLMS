"""
Management command to force enable SMTP email backend
"""
from django.core.management.base import BaseCommand
import os


class Command(BaseCommand):
    help = 'Enable SMTP email backend by updating environment'

    def handle(self, *args, **options):
        # Set environment variable for current session
        os.environ['EMAIL_BACKEND'] = 'django.core.mail.backends.smtp.EmailBackend'
        
        # Update .env file
        env_file = '.env'
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                lines = f.readlines()
            
            # Update or add EMAIL_BACKEND line
            updated = False
            new_lines = []
            for line in lines:
                if line.startswith('EMAIL_BACKEND='):
                    new_lines.append('EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend\n')
                    updated = True
                else:
                    new_lines.append(line)
            
            if not updated:
                new_lines.append('EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend\n')
            
            with open(env_file, 'w') as f:
                f.writelines(new_lines)
            
            self.stdout.write(
                self.style.SUCCESS('✅ SMTP email backend enabled!')
            )
            self.stdout.write(
                'Note: You may need to restart the Django development server for changes to take effect.'
            )
        else:
            self.stdout.write(
                self.style.ERROR('❌ .env file not found')
            )
