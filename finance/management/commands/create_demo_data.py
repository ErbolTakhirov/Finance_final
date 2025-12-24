from datetime import date, timedelta
from decimal import Decimal
import random

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from finance.services.accounting import AccountingService
from goals.services import GoalService


class Command(BaseCommand):
    help = 'Create demo user, demo transactions (>= 6 months), and demo goals'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='demo', help='Demo username')
        parser.add_argument('--password', default='demo12345', help='Demo password')

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']

        user, created = User.objects.get_or_create(username=username)
        if created:
            user.set_password(password)
            user.save()

        today = date.today().replace(day=1)

        for i in range(6, -1, -1):
            month_start = (today - timedelta(days=30 * i)).replace(day=1)
            # income
            AccountingService.create_transaction(
                user=user,
                date=month_start.replace(day=5),
                amount=Decimal(str(50000 + random.randint(-4000, 8000))),
                type='income',
                category='Зарплата',
                description='Основной доход',
                source='demo',
            )

            expenses = [
                ('Аренда', 15000, 2),
                ('Еда', 12000 + random.randint(-1500, 3000), 10),
                ('Транспорт', 3500 + random.randint(0, 1500), 15),
                ('Развлечения', 5000 + random.randint(-500, 5000), 20),
            ]

            for cat, amt, day in expenses:
                AccountingService.create_transaction(
                    user=user,
                    date=month_start.replace(day=day),
                    amount=Decimal(str(amt)),
                    type='expense',
                    category=cat,
                    description='Демо-расход',
                    source='demo',
                )

        GoalService.create_goal(
            user=user,
            title='Финансовая подушка',
            description='Накопить резерв на 3 месяца расходов',
            target_amount=Decimal('200000.00'),
            target_date=date.today() + timedelta(days=365),
        )

        GoalService.create_goal(
            user=user,
            title='Новый ноутбук',
            description='Для работы и обучения',
            target_amount=Decimal('120000.00'),
            target_date=date.today() + timedelta(days=240),
        )

        self.stdout.write(self.style.SUCCESS(f"Demo data created for user={username}, password={password}"))
