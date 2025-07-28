"""
Management command to verify system configuration is properly implemented across modules.
This will check for hardcoded currency symbols, company names, etc.
"""

from django.core.management.base import BaseCommand
from django.conf import settings
import os
import re


class Command(BaseCommand):
    help = 'Verify that system configuration is correctly implemented across modules'
    
    def handle(self, *args, **options):
        self.stdout.write('Starting system configuration verification...')
        
        # Check template files for hardcoded currency symbols
        template_dir = os.path.join(settings.BASE_DIR, 'templates')
        hardcoded_patterns = [
            r'₦\{',  # Hardcoded Naira symbol in JS template literals
            r'₦\d',  # Hardcoded Naira symbol with digit
            r'₦\{',  # Hardcoded Naira symbol in template literals
            r'₦\s',  # Hardcoded Naira symbol with space
            r'₦<',   # Hardcoded Naira symbol before tag
            r'"₦',   # Hardcoded Naira symbol in quotes
            r'\'₦',  # Hardcoded Naira symbol in single quotes
            r'>₦',   # Hardcoded Naira symbol after tag
            r'\sNGN\s',  # Hardcoded NGN
            r'>\s*NGN\s*<',  # Hardcoded NGN between tags
            r'Naira',  # Hardcoded Naira word
            r'naira',  # Hardcoded naira word
            r'Niara',  # Common misspelling
            r'niara',  # Common misspelling
        ]
        
        issues_found = []
        template_count = 0
        
        # Walk through the template directory
        for root, _, files in os.walk(template_dir):
            for file in files:
                if file.endswith('.html'):
                    template_count += 1
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, settings.BASE_DIR)
                    
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        line_number = 1
                        for line in content.split('\n'):
                            for pattern in hardcoded_patterns:
                                matches = re.search(pattern, line)
                                if matches and '{{ CURRENCY_SYMBOL }}' not in line and '{{ system_config.currency_symbol }}' not in line:
                                    # Check if it's in a comment
                                    if '<!--' not in line or '-->' not in line:
                                        issues_found.append({
                                            'file': relative_path,
                                            'line': line_number,
                                            'content': line.strip(),
                                            'pattern': pattern
                                        })
                            line_number += 1
        
        # Report findings
        self.stdout.write(f"Scanned {template_count} templates")
        
        if issues_found:
            self.stdout.write(f"Found {len(issues_found)} potential hardcoded currency issues:")
            for issue in issues_found:
                self.stdout.write(
                    f"{issue['file']} (line {issue['line']}): {issue['content']}"
                )
            self.stdout.write(
                "Replace hardcoded currency symbols with {{ CURRENCY_SYMBOL }} "
                "or {{ system_config.currency_symbol }}"
            )
        else:
            self.stdout.write("No hardcoded currency issues found!")
        
        # Check model __str__ methods
        self.stdout.write("\nChecking model __str__ methods...")
        self.stdout.write(
            "Please manually review __str__ methods in the following files:\n"
            "- services/models.py\n"
            "- expenses/models.py\n"
            "- orders/models.py\n"
            "to ensure they use SystemConfiguration.get_config().currency_symbol"
        )
        
        # Final recommendations
        self.stdout.write("\nFinal recommendations:")
        self.stdout.write("1. Ensure all templates use {{ CURRENCY_SYMBOL }} from the context processor")
        self.stdout.write("2. For JavaScript, pass the currency symbol using a variable: const currencySymbol = \"{{ CURRENCY_SYMBOL }}\"")
        self.stdout.write("3. In model methods, use SystemConfiguration.get_config().currency_symbol")
        self.stdout.write("4. Test by changing currency symbol in admin and checking all pages")
