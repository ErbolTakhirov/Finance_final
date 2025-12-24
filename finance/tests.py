from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from finance.models import MonthlySummary
from finance.services.accounting import AccountingService
from finance.services.forecast import ForecastService


class MonthlySummaryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u1', password='pass')

    def test_monthly_summary_recalculation(self):
        AccountingService.create_transaction(
            user=self.user,
            date=date(2025, 1, 5),
            amount=Decimal('1000.00'),
            type='income',
            category='Salary',
        )
        AccountingService.create_transaction(
            user=self.user,
            date=date(2025, 1, 10),
            amount=Decimal('200.00'),
            type='expense',
            category='Food',
        )
        AccountingService.create_transaction(
            user=self.user,
            date=date(2025, 1, 15),
            amount=Decimal('50.00'),
            type='expense',
            category='Transport',
        )

        summary = MonthlySummary.objects.get(user=self.user, month_key='2025-01')
        self.assertEqual(summary.total_income, Decimal('1000.00'))
        self.assertEqual(summary.total_expense, Decimal('250.00'))
        self.assertEqual(summary.profit, Decimal('750.00'))


class ForecastServiceTests(TestCase):
    def test_insufficient_data(self):
        class S:
            def __init__(self, month_key, profit):
                self.month_key = month_key
                self.profit = profit

        result = ForecastService.forecast_next_month([
            S('2025-01', Decimal('100')),
            S('2025-02', Decimal('110')),
        ])
        self.assertEqual(result.status, 'insufficient_data')

    def test_forecast_ok(self):
        class S:
            def __init__(self, month_key, profit):
                self.month_key = month_key
                self.profit = profit

        history = [
            S('2025-01', Decimal('100')),
            S('2025-02', Decimal('110')),
            S('2025-03', Decimal('120')),
        ]
        result = ForecastService.forecast_next_month(history)
        self.assertEqual(result.status, 'ok')
        self.assertIsNotNone(result.predicted_profit)
        # Trend is +10/month, so next should be near 130
        self.assertTrue(Decimal('120') <= result.predicted_profit <= Decimal('140'))
