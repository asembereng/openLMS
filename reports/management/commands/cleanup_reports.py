"""
Management command to cleanup expired reports
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from reports.models import GeneratedReport


class Command(BaseCommand):
    help = 'Cleanup expired reports'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force cleanup without confirmation',
        )

    def handle(self, *args, **options):
        self.stdout.write('Starting report cleanup...')
        
        # Find expired reports
        expired_reports = GeneratedReport.objects.filter(
            expires_at__lt=timezone.now()
        ).exclude(expires_at__isnull=True)
        
        count = expired_reports.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('No expired reports found.')  # type: ignore
            )
            return
        
        self.stdout.write(f'Found {count} expired reports:')
        
        # Show details of expired reports
        for report in expired_reports:
            age = timezone.now() - report.generated_at
            expired_since = timezone.now() - report.expires_at
            self.stdout.write(
                f'  - {report.title} (generated {age.days} days ago, '
                f'expired {expired_since.days} days and {expired_since.seconds//3600} hours ago)'
            )
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING('DRY RUN: No reports were deleted.')  # type: ignore
            )
            return
        
        # Confirm deletion unless forced
        if not options['force']:
            confirm = input(f'Delete {count} expired reports? [y/N]: ')
            if confirm.lower() not in ['y', 'yes']:
                self.stdout.write('Cleanup cancelled.')
                return
        
        # Delete expired reports
        deleted_count, _ = expired_reports.delete()
        
        self.stdout.write(
            self.style.SUCCESS(  # type: ignore
                f'Successfully deleted {deleted_count} expired reports.'
            )
        )
