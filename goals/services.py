from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from django.db import transaction as db_transaction

from goals.models import Goal
from finance.models import MonthlySummary


@dataclass
class GoalProgress:
    current_saved: Decimal
    progress_percent: int
    projected_date: Optional[date]
    probability_of_success: int


class GoalService:
    """Business logic for financial goals and progress tracking."""

    @staticmethod
    @db_transaction.atomic
    def create_goal(
        *,
        user,
        title: str,
        description: str,
        target_amount: Decimal,
        target_date: date,
    ) -> Goal:
        goal = Goal(
            user=user,
            title=title,
            description=description,
            target_amount=target_amount,
            target_date=target_date,
            status='active',
        )
        goal.full_clean()
        goal.save()
        return goal

    @staticmethod
    @db_transaction.atomic
    def update_goal(goal: Goal, **fields) -> Goal:
        for k, v in fields.items():
            setattr(goal, k, v)
        goal.full_clean()
        goal.save()
        return goal

    @staticmethod
    def calculate_progress(goal: Goal) -> GoalProgress:
        """
        Calculate current progress and projections.
        """
        current = goal.current_saved
        progress = goal.progress_percent

        summaries = MonthlySummary.objects.filter(user=goal.user).order_by('-month_key')[:3]

        if summaries.count() < 1:
            return GoalProgress(
                current_saved=current,
                progress_percent=progress,
                projected_date=None,
                probability_of_success=0,
            )

        total = sum(s.profit for s in summaries)
        avg_profit = total / len(summaries)

        remaining = goal.target_amount - current
        days_left = (goal.target_date - date.today()).days

        if avg_profit <= 0:
            projected_date = None
            probability = 5
        else:
            months_needed = float(remaining) / float(avg_profit)
            projected_date = date.today() + timedelta(days=int(months_needed * 30))

            months_left = days_left / 30.0
            if months_left <= 0:
                probability = 0
            elif months_needed <= months_left:
                probability = min(99, 70 + int((months_left - months_needed) * 10))
            else:
                probability = max(5, 50 - int((months_needed - months_left) * 10))

        return GoalProgress(
            current_saved=current,
            progress_percent=progress,
            projected_date=projected_date,
            probability_of_success=probability,
        )

    @staticmethod
    @db_transaction.atomic
    def auto_update_statuses(user) -> int:
        """
        Update goals statuses based on current state:
        - Achieved if current_saved >= target_amount
        - Failed if target_date passed and not achieved
        """
        updated = 0
        goals = Goal.objects.filter(user=user, status='active')
        today = date.today()

        for goal in goals:
            if goal.current_saved >= goal.target_amount:
                goal.status = 'achieved'
                goal.save()
                updated += 1
            elif goal.target_date < today:
                goal.status = 'failed'
                goal.save()
                updated += 1

        return updated
