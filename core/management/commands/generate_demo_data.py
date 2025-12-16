"""
Django management command to generate realistic demo data for ML testing
"""

import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Income, Expense


class Command(BaseCommand):
    help = 'Generate realistic demo financial data for ML testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=365,
            help='Number of days of data to generate (default: 365)'
        )
        parser.add_argument(
            '--username',
            type=str,
            default='demo',
            help='Username for demo data (default: demo)'
        )

    def handle(self, *args, **options):
        days = options['days']
        username = options['username']
        
        # Get or create demo user
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': f'{username}@example.com',
                'first_name': 'Demo',
                'last_name': 'User'
            }
        )
        
        if created:
            user.set_password('demo123')
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Created user: {username}'))
        else:
            self.stdout.write(self.style.WARNING(f'User {username} already exists'))
        
        # Clear existing data
        Income.objects.filter(user=user).delete()
        Expense.objects.filter(user=user).delete()
        
        # Income categories with typical amounts
        income_categories = {
            'sales': (20000, 50000),
            'services': (15000, 40000),
            'consulting': (30000, 80000),
            'products': (10000, 30000),
            'other': (5000, 20000)
        }
        
        # Expense categories with typical amounts
        expense_categories = {
            'rent': (25000, 30000),
            'salary': (80000, 120000),
            'tax': (15000, 40000),
            'marketing': (10000, 50000),
            'purchase': (5000, 30000),
            'utilities': (3000, 8000),
            'transport': (2000, 10000),
            'food': (5000, 15000),
            'equipment': (10000, 50000),
            'services': (5000, 20000),
            'insurance': (5000, 15000),
            'other': (1000, 10000)
        }
        
        start_date = datetime.now() - timedelta(days=days)
        
        # Generate income transactions
        income_count = 0
        for day in range(days):
            current_date = start_date + timedelta(days=day)
            
            # Skip weekends for some income
            is_weekend = current_date.weekday() >= 5
            
            # 30% chance of income per day, 10% on weekends
            if random.random() < (0.1 if is_weekend else 0.3):
                category = random.choice(list(income_categories.keys()))
                min_amount, max_amount = income_categories[category]
                
                # Add some seasonality (higher in Q4, lower in summer)
                month = current_date.month
                seasonal_factor = 1.0
                if month in [11, 12]:
                    seasonal_factor = 1.3
                elif month in [6, 7, 8]:
                    seasonal_factor = 0.8
                
                amount = random.uniform(min_amount, max_amount) * seasonal_factor
                
                Income.objects.create(
                    user=user,
                    amount=round(amount, 2),
                    date=current_date.date(),
                    category=category,
                    description=f'Income from {category} - {current_date.strftime("%B %d")}'
                )
                income_count += 1
        
        # Generate expense transactions
        expense_count = 0
        for day in range(days):
            current_date = start_date + timedelta(days=day)
            is_weekend = current_date.weekday() >= 5
            
            # More frequent expenses
            num_expenses = random.randint(1, 4) if not is_weekend else random.randint(0, 2)
            
            for _ in range(num_expenses):
                category = random.choice(list(expense_categories.keys()))
                min_amount, max_amount = expense_categories[category]
                
                # Monthly recurring expenses
                if category in ['rent', 'salary', 'insurance'] and current_date.day == 1:
                    amount = random.uniform(max_amount * 0.9, max_amount)
                else:
                    amount = random.uniform(min_amount, max_amount)
                
                # Add some randomness and anomalies (5% chance of very high expense)
                if random.random() < 0.05:
                    amount *= random.uniform(2.0, 4.0)  # Anomaly!
                
                Expense.objects.create(
                    user=user,
                    amount=round(amount, 2),
                    date=current_date.date(),
                    category=category,
                    description=f'{category.capitalize()} expense - {current_date.strftime("%B %d")}'
                )
                expense_count += 1
        
        # Calculate statistics
        total_income = Income.objects.filter(user=user).aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        
        total_expense = Expense.objects.filter(user=user).aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        
        profit = total_income - total_expense
        
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS(f'Demo data generated successfully!'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'User: {username}')
        self.stdout.write(f'Period: {days} days')
        self.stdout.write(f'Income transactions: {income_count}')
        self.stdout.write(f'Expense transactions: {expense_count}')
        self.stdout.write(f'Total income: {total_income:,.2f}')
        self.stdout.write(f'Total expenses: {total_expense:,.2f}')
        self.stdout.write(f'Profit: {profit:,.2f}')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.WARNING(f'\nLogin credentials:'))
        self.stdout.write(f'  Username: {username}')
        self.stdout.write(f'  Password: demo123')
        self.stdout.write(self.style.SUCCESS('=' * 60))


# Import models for Sum
from django.db import models
