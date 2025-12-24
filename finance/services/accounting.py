from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Dict, List

from django.db import transaction as db_transaction
from django.db.models import Sum

from finance.models import Transaction, MonthlySummary


@dataclass
class MonthlyAggregates:
    month_key: str
    total_income: Decimal
    total_expense: Decimal
    profit: Decimal


class AccountingService:
    """Business logic for financial accounting and monthly aggregation."""

    @staticmethod
    @db_transaction.atomic
    def create_transaction(
        *,
        user,
        date,
        amount: Decimal,
        type: str,
        category: str,
        description: str = "",
        source: str = "manual",
        is_verified: bool = True,
    ) -> Transaction:
        tx = Transaction(
            user=user,
            date=date,
            amount=amount,
            type=type,
            category=category,
            description=description,
            source=source,
            is_verified=is_verified,
            month_key=date.strftime('%Y-%m'),
        )
        tx.full_clean()
        tx.save()
        AccountingService.recalculate_month(user=user, month_key=tx.month_key)
        return tx

    @staticmethod
    @db_transaction.atomic
    def update_transaction(*, tx: Transaction, **fields) -> Transaction:
        old_month_key = tx.month_key
        for k, v in fields.items():
            setattr(tx, k, v)
        if 'date' in fields:
            tx.month_key = tx.date.strftime('%Y-%m')
        tx.full_clean()
        tx.save()

        AccountingService.recalculate_month(user=tx.user, month_key=old_month_key)
        AccountingService.recalculate_month(user=tx.user, month_key=tx.month_key)
        return tx

    @staticmethod
    @db_transaction.atomic
    def delete_transaction(*, tx: Transaction) -> None:
        month_key = tx.month_key
        user = tx.user
        tx.delete()
        AccountingService.recalculate_month(user=user, month_key=month_key)

    @staticmethod
    def recalculate_month(*, user, month_key: str) -> MonthlySummary:
        summary, _ = MonthlySummary.objects.get_or_create(user=user, month_key=month_key)
        summary.recalculate()
        return summary

    @staticmethod
    def get_months(*, user) -> List[str]:
        return list(
            MonthlySummary.objects.filter(user=user)
            .order_by('-month_key')
            .values_list('month_key', flat=True)
        )

    @staticmethod
    def top_expense_categories(*, user, month_key: str, limit: int = 5) -> List[Dict[str, object]]:
        qs = (
            Transaction.objects.filter(user=user, month_key=month_key, type='expense')
            .values('category')
            .annotate(total=Sum('amount'))
            .order_by('-total')
        )
        return [
            {
                'category': row['category'],
                'total': row['total'] or Decimal('0'),
            }
            for row in qs[:limit]
        ]

    @staticmethod
    def current_month_summary(*, user) -> Optional[MonthlySummary]:
        from django.utils import timezone

        month_key = timezone.now().date().strftime('%Y-%m')
        return MonthlySummary.objects.filter(user=user, month_key=month_key).first()
