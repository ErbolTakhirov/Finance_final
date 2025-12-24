from __future__ import annotations

import re
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


_MONTH_KEY_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class Transaction(models.Model):
    """Unified transaction model for income and expenses.

    Important: `amount` is always positive. `type` determines whether it is income or expense.
    """

    TYPE_CHOICES = [
        ("income", "Доход"),
        ("expense", "Расход"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transactions")
    date = models.DateField(help_text="Transaction date")
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Amount (positive). Type determines if income or expense.",
    )
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    category = models.CharField(max_length=100, help_text="Category (e.g., Зарплата, Еда, Аренда)")
    description = models.TextField(blank=True, help_text="Optional description")
    source = models.CharField(max_length=50, default="manual", help_text="Source of transaction")
    is_verified = models.BooleanField(default=True, help_text="Whether transaction is verified")

    month_key = models.CharField(max_length=7, db_index=True, help_text="Format: YYYY-MM")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"
        ordering = ["-date", "-created_at"]
        indexes = [
            models.Index(fields=["user", "date"]),
            models.Index(fields=["user", "month_key"]),
            models.Index(fields=["user", "type"]),
        ]

    def save(self, *args, **kwargs):
        # Keep month_key consistent with date even on updates.
        self.month_key = self.date.strftime("%Y-%m")
        super().save(*args, **kwargs)

    def clean(self):
        errors = {}

        if self.amount is None or self.amount <= 0:
            errors["amount"] = "Amount must be greater than 0"

        if self.month_key and not _MONTH_KEY_RE.match(self.month_key):
            errors["month_key"] = "Month key must be in YYYY-MM format"

        expected = self.date.strftime("%Y-%m") if self.date else None
        if expected and self.month_key and self.month_key != expected:
            errors["month_key"] = "Month key must match the transaction date"

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        sign = "+" if self.type == "income" else "-"
        return f"{sign}{self.amount} {self.category} ({self.date})"


class MonthlySummary(models.Model):
    """Monthly aggregation of income, expenses, and profit."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="monthly_summaries")
    month_key = models.CharField(max_length=7, db_index=True, help_text="Format: YYYY-MM")

    total_income = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    total_expense = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    profit = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Monthly Summary"
        verbose_name_plural = "Monthly Summaries"
        unique_together = ["user", "month_key"]
        ordering = ["-month_key"]
        indexes = [
            models.Index(fields=["user", "month_key"]),
        ]

    def recalculate(self) -> None:
        """Recalculate summary from user's transactions for this month."""

        transactions = Transaction.objects.filter(user=self.user, month_key=self.month_key)

        income = (
            transactions.filter(type="income")
            .aggregate(total=models.Sum("amount"))
            .get("total")
            or Decimal("0")
        )

        expense = (
            transactions.filter(type="expense")
            .aggregate(total=models.Sum("amount"))
            .get("total")
            or Decimal("0")
        )

        self.total_income = income
        self.total_expense = expense
        self.profit = income - expense
        self.save(update_fields=["total_income", "total_expense", "profit", "updated_at"])

    def __str__(self):
        return f"{self.user.username} - {self.month_key}: Profit {self.profit}"


class CategoryBudget(models.Model):
    """Budget limits for expense categories."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="category_budgets")
    category = models.CharField(max_length=100)
    monthly_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Category Budget"
        verbose_name_plural = "Category Budgets"
        unique_together = ["user", "category"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self):
        return f"{self.category}: {self.monthly_limit} ({self.user.username})"
