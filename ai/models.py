from django.db import models
from django.contrib.auth.models import User


class AIRecommendationLog(models.Model):
    """
    Log of AI recommendations and advice
    """
    TYPE_CHOICES = [
        ('monthly_report', 'Monthly Report'),
        ('goal_advice', 'Goal Progress Advice'),
        ('forecast_explanation', 'Forecast Explanation'),
        ('general_advice', 'General Financial Advice'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_recs')
    goal = models.ForeignKey('goals.Goal', on_delete=models.SET_NULL, null=True, blank=True)
    month_key = models.CharField(max_length=7, blank=True, help_text='Format: YYYY-MM')
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    content = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'AI Recommendation'
        verbose_name_plural = 'AI Recommendations'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['user', 'goal']),
            models.Index(fields=['month_key']),
        ]

    def __str__(self):
        return f"{self.get_type_display()} for {self.user.username} - {self.created_at.date()}"
