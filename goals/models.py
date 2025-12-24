from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal


class Goal(models.Model):
    """Financial goals with progress tracking"""

    STATUS_CHOICES = [
        ('active', 'Активная'),
        ('achieved', 'Достигнута'),
        ('failed', 'Не достигнута'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='finance_goals')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    target_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    target_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Goal'
        verbose_name_plural = 'Goals'
        ordering = ['status', 'target_date']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'target_date']),
        ]

    def clean(self):
        if self.target_amount <= 0:
            raise ValidationError({'target_amount': 'Target amount must be greater than 0'})
        if self.target_date <= timezone.now().date():
            raise ValidationError({'target_date': 'Target date must be in the future'})

    @property
    def current_saved(self) -> Decimal:
        """Current saved amount computed from cumulative monthly profits.

        For a goal-centric accountant demo we treat "saved" as net profit accumulated
        across months available in the system.
        """
        from finance.models import MonthlySummary

        summaries = MonthlySummary.objects.filter(user=self.user)
        total_profit = summaries.aggregate(total=models.Sum('profit'))['total'] or Decimal('0')
        return max(Decimal('0'), total_profit)

    @property
    def progress_percent(self) -> int:
        if self.target_amount <= 0:
            return 0
        percent = (self.current_saved / self.target_amount) * 100
        return int(min(100, max(0, percent)))

    def __str__(self):
        return f"{self.title} ({self.progress_percent}%)"
