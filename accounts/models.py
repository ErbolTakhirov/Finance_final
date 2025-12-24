from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    """
    Extended user profile for personal finance management
    """
    CURRENCY_CHOICES = [
        ('KGS', 'Кыргызский сом'),
        ('USD', 'US Dollar'),
        ('EUR', 'Euro'),
        ('RUB', 'Российский рубль'),
    ]
    
    LOCALE_CHOICES = [
        ('ru', 'Русский'),
        ('en', 'English'),
        ('ky', 'Кыргызча'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='KGS')
    locale = models.CharField(max_length=5, choices=LOCALE_CHOICES, default='ru')
    timezone = models.CharField(max_length=50, default='Asia/Bishkek')
    
    # Privacy settings
    auto_anonymize = models.BooleanField(default=True, help_text='Anonymize data before sending to cloud LLM')
    use_local_llm = models.BooleanField(default=False, help_text='Use local Ollama instead of cloud')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        indexes = [
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"Profile: {self.user.username} ({self.currency})"
