from django.urls import path
from . import views_teen

# Namespace for teen routes
app_name = 'teen'

urlpatterns = [
    # Teen Dashboard and Core Features
    path('', views_teen.teen_dashboard, name='dashboard'),
    path('goals/', views_teen.goals_view, name='goals'),
    path('goals/create/', views_teen.create_goal, name='create_goal'),
    path('goals/update/<int:goal_id>/', views_teen.update_goal_progress, name='update_goal_progress'),
    
    # AI Coach Chat
    path('ai-coach/', views_teen.ai_coach, name='ai_coach'),
    
    # Learning and Education
    path('learning/', views_teen.learning_modules, name='learning'),
    path('learning/module/<int:module_id>/', views_teen.module_detail, name='module_detail'),
    path('quiz/<int:quiz_id>/', views_teen.take_quiz, name='take_quiz'),
    
    # Gamification
    path('achievements/', views_teen.achievements_view, name='achievements'),
    
    # Security and Safety
    path('scam-awareness/', views_teen.scam_awareness, name='scam_awareness'),
    
    # Demo Mode
    path('toggle-demo/', views_teen.toggle_demo_mode, name='toggle_demo_mode'),
    
    # API endpoints for teen features
    path('api/chat/', views_teen.chat_with_ai, name='api_chat'),
    path('api/scam-report/', views_teen.report_scam, name='api_scam_report'),
    path('api/refresh-stats/', views_teen.refresh_stats, name='refresh_stats'),
]