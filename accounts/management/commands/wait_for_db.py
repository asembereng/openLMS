"""
Management command to wait for database to be available.
Useful for Docker deployments where the database might not be ready immediately.
"""
import time
from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError


class Command(BaseCommand):
    """Django command to pause execution until database is available"""
    
    help = 'Wait for database to be available'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--timeout',
            type=int,
            default=30,
            help='Maximum time to wait for database (seconds)',
        )
        parser.add_argument(
            '--check-interval',
            type=int,
            default=1,
            help='Time between database checks (seconds)',
        )
    
    def handle(self, *args, **options):
        timeout = options['timeout']
        check_interval = options['check_interval']
        
        self.stdout.write('Waiting for database...')
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Try to connect to the database
                db_conn = connections['default']
                db_conn.cursor()
                self.stdout.write('Database available!')
                return
            except OperationalError:
                self.stdout.write(
                    f'Database unavailable, waiting {check_interval} second(s)...'
                )
                time.sleep(check_interval)
        
        self.stdout.write(f'Database unavailable after {timeout} seconds!')
        exit(1)
