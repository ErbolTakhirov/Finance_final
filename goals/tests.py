from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from finance.models import MonthlySummary
from goals.models import Goal
from goals.services import GoalService


class GoalProgressTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u1', password='pass')

    def test_goal_progress_percent(self):
        # Create goal first with date in future
        goal = Goal.objects.create(
            user=self.user,
            title='Save for laptop',
            description='',
            target_amount=Decimal('1000.00'),
            target_date=date.today() + timedelta(days=180),
            status='active',
        )

        # Then create monthly summaries (must be >= goal.created_at month)
        # Goal created now, so profit from this month onwards counts
        current_month = date.today().strftime('%Y-%m')
        MonthlySummary.objects.create(user=self.user, month_key=current_month, total_income=1000, total_expense=900, profit=100)

        # Refresh goal to get updated current_saved
        goal.refresh_from_db()
        self.assertEqual(goal.current_saved, Decimal('100'))
        self.assertEqual(goal.progress_percent, 10)

        progress = GoalService.calculate_progress(goal)
        self.assertEqual(progress.current_saved, Decimal('100'))
        self.assertEqual(progress.progress_percent, 10)

    def test_goal_auto_status_update(self):
        goal = Goal.objects.create(
            user=self.user,
            title='Goal',
            description='',
            target_amount=Decimal('500.00'),
            target_date=date.today() + timedelta(days=10),
            status='active',
        )

        current_month = date.today().strftime('%Y-%m')
        MonthlySummary.objects.create(user=self.user, month_key=current_month, total_income=1000, total_expense=0, profit=1000)

        updated = GoalService.auto_update_statuses(self.user)
        self.assertEqual(updated, 1)

        goal.refresh_from_db()
        self.assertEqual(goal.status, 'achieved')
