from django.urls import path
from ai import views

urlpatterns = [
    path('monthly-report/', views.monthly_report, name='ai-monthly-report'),
    path('goal-advice/', views.goal_advice, name='ai-goal-advice'),
    path('forecast/', views.forecast_view, name='ai-forecast'),
]
