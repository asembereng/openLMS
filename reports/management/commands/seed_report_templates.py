from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from reports.models import ReportTemplate


class Command(BaseCommand):
    help = 'Seed initial report templates for the Laundry Management System'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force creation even if templates exist',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        
        # Check if templates already exist
        existing_count = ReportTemplate.objects.count()
        if existing_count > 0 and not force:
            self.stdout.write(
                self.style.WARNING(
                    f'Found {existing_count} existing report templates. '
                    f'Use --force to recreate them.'
                )
            )
            return

        if force and existing_count > 0:
            self.stdout.write('Deleting existing report templates...')
            ReportTemplate.objects.all().delete()

        # Get or create admin user for created_by field
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            self.stdout.write(
                self.style.ERROR(
                    'No admin user found. Please create an admin user first.'
                )
            )
            return

        # Define initial report templates
        templates = [
            {
                'name': 'Daily Sales Summary',
                'report_type': 'daily_sales',
                'description': 'Summary of daily sales including total revenue, order count, and top services.',
                'config': {
                    'chart_types': ['line', 'bar'],
                    'metrics': ['total_revenue', 'order_count', 'avg_order_value'],
                    'grouping': 'by_hour',
                    'filters': ['service_type', 'customer_type'],
                    'default_period': 'today'
                },
                'is_public': True,
                'allowed_roles': ['admin', 'manager', 'staff']
            },
            {
                'name': 'Weekly Sales Analysis',
                'report_type': 'daily_sales',
                'description': 'Comprehensive weekly sales analysis with trends and comparisons.',
                'config': {
                    'chart_types': ['line', 'area'],
                    'metrics': ['total_revenue', 'order_count', 'customer_count'],
                    'grouping': 'by_day',
                    'filters': ['service_type', 'payment_method'],
                    'default_period': 'last_7_days',
                    'comparison': 'previous_week'
                },
                'is_public': False,
                'allowed_roles': ['admin', 'manager']
            },
            {
                'name': 'Monthly Profit & Loss',
                'report_type': 'monthly_profit',
                'description': 'Monthly profitability report including revenue, expenses, and net profit.',
                'config': {
                    'chart_types': ['bar', 'pie'],
                    'metrics': ['total_revenue', 'total_expenses', 'net_profit', 'profit_margin'],
                    'grouping': 'by_month',
                    'filters': ['expense_category', 'service_type'],
                    'default_period': 'current_month',
                    'expense_categories': True,
                    'profit_breakdown': True
                },
                'is_public': False,
                'allowed_roles': ['admin', 'manager']
            },
            {
                'name': 'Customer Statement',
                'report_type': 'customer_statement',
                'description': 'Individual customer statement showing orders, payments, and outstanding balance.',
                'config': {
                    'chart_types': ['table'],
                    'metrics': ['total_orders', 'total_amount', 'amount_paid', 'balance'],
                    'grouping': 'by_order',
                    'filters': ['date_range', 'payment_status'],
                    'include_order_details': True,
                    'show_payment_history': True
                },
                'is_public': True,
                'allowed_roles': ['admin', 'manager', 'staff']
            },
            {
                'name': 'Monthly Expense Summary',
                'report_type': 'expense_summary',
                'description': 'Monthly expense breakdown by category with budget comparisons.',
                'config': {
                    'chart_types': ['pie', 'bar'],
                    'metrics': ['total_expenses', 'expense_by_category', 'budget_variance'],
                    'grouping': 'by_category',
                    'filters': ['expense_category', 'date_range'],
                    'default_period': 'current_month',
                    'budget_comparison': True
                },
                'is_public': False,
                'allowed_roles': ['admin', 'manager']
            },
            {
                'name': 'Service Performance Analysis',
                'report_type': 'service_analysis',
                'description': 'Analysis of service performance including popularity, revenue, and profitability.',
                'config': {
                    'chart_types': ['bar', 'pie', 'line'],
                    'metrics': ['service_revenue', 'order_count', 'avg_pieces', 'profit_margin'],
                    'grouping': 'by_service',
                    'filters': ['service_type', 'date_range'],
                    'default_period': 'last_30_days',
                    'top_services': 10,
                    'profitability_analysis': True
                },
                'is_public': False,
                'allowed_roles': ['admin', 'manager']
            },
            {
                'name': 'Daily Operations Dashboard',
                'report_type': 'custom',
                'description': 'Daily operations overview for staff with key metrics and pending orders.',
                'config': {
                    'chart_types': ['card', 'table'],
                    'metrics': ['pending_orders', 'completed_orders', 'daily_revenue', 'customers_served'],
                    'grouping': 'real_time',
                    'filters': ['order_status', 'priority'],
                    'default_period': 'today',
                    'refresh_interval': 300,  # 5 minutes
                    'show_pending_orders': True
                },
                'is_public': True,
                'allowed_roles': ['admin', 'manager', 'staff']
            },
            {
                'name': 'Customer Growth Report',
                'report_type': 'custom',
                'description': 'Customer acquisition and retention analysis with growth trends.',
                'config': {
                    'chart_types': ['line', 'bar'],
                    'metrics': ['new_customers', 'returning_customers', 'customer_lifetime_value', 'retention_rate'],
                    'grouping': 'by_month',
                    'filters': ['customer_type', 'registration_source'],
                    'default_period': 'last_12_months',
                    'cohort_analysis': True,
                    'growth_rate': True
                },
                'is_public': False,
                'allowed_roles': ['admin', 'manager']
            },
            {
                'name': 'Quarterly Business Review',
                'report_type': 'custom',
                'description': 'Comprehensive quarterly business review with all key metrics and insights.',
                'config': {
                    'chart_types': ['line', 'bar', 'pie', 'table'],
                    'metrics': [
                        'quarterly_revenue', 'quarterly_profit', 'customer_growth',
                        'service_performance', 'expense_analysis', 'key_insights'
                    ],
                    'grouping': 'by_quarter',
                    'filters': ['compare_quarters'],
                    'default_period': 'current_quarter',
                    'executive_summary': True,
                    'actionable_insights': True,
                    'forecasting': True
                },
                'is_public': False,
                'allowed_roles': ['admin']
            }
        ]

        created_count = 0
        for template_data in templates:
            template, created = ReportTemplate.objects.get_or_create(
                name=template_data['name'],
                report_type=template_data['report_type'],
                defaults={
                    'description': template_data['description'],
                    'config': template_data['config'],
                    'is_public': template_data['is_public'],
                    'allowed_roles': template_data['allowed_roles'],
                    'created_by': admin_user,
                    'is_active': True
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created report template: {template.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Template already exists: {template.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSeeding completed! Created {created_count} new report templates.'
            )
        )
        
        if created_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    'You can now visit the Reports section to view and use these templates.'
                )
            )
