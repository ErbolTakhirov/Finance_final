from django.contrib import admin
from .models import (
    Income, Expense, Event, Document, ChatSession, ChatMessage, UploadedFile, 
    UserProfile, UserGoal, Achievement, LearningModule, TeenChatSession, ScamAlert,
    UserProgress, UserAchievement, Quiz, QuizQuestion, UserQuizAttempt,
    FinancialInsight
)


@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ('date', 'amount', 'income_type', 'user')
    list_filter = ('income_type', 'date', 'user')
    search_fields = ('description', 'user__username')


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('date', 'amount', 'expense_type', 'user')
    list_filter = ('expense_type', 'date', 'user')
    search_fields = ('description', 'user__username')


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('date', 'title', 'user')
    list_filter = ('date', 'user')
    search_fields = ('title', 'description', 'user__username')


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'doc_type', 'user', 'created_at')
    list_filter = ('doc_type', 'created_at', 'user')
    search_fields = ('user__username',)


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ('original_name', 'file_type', 'user', 'file_size', 'uploaded_at', 'processed')
    list_filter = ('file_type', 'processed', 'uploaded_at', 'user')
    search_fields = ('original_name', 'user__username')
    readonly_fields = ('uploaded_at', 'file_size')


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'title', 'user', 'created_at', 'updated_at', 'message_count')
    list_filter = ('created_at', 'user')
    readonly_fields = ('created_at', 'updated_at')
    search_fields = ('session_id', 'title', 'user__username')
    
    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = 'Сообщений'


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'role', 'content_preview', 'user', 'created_at')
    list_filter = ('role', 'created_at', 'session')
    readonly_fields = ('created_at', 'content_hash')
    search_fields = ('content', 'session__session_id', 'session__user__username')
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Содержание'
    
    def user(self, obj):
        return obj.session.user if obj.session.user else None
    user.short_description = 'Пользователь'


# Teen-specific models
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'age', 'financial_iq_score', 'total_achievements', 'current_streak')
    list_filter = ('age', 'preferred_language', 'demo_mode')
    search_fields = ('user__username', 'user__email')


@admin.register(UserGoal)
class UserGoalAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'category', 'progress_percentage', 'target_date', 'status')
    list_filter = ('category', 'status', 'target_date')
    search_fields = ('user__username', 'title', 'description')
    
    def progress_percentage(self, obj):
        return f"{obj.progress_percentage():.0f}%"
    progress_percentage.short_description = 'Прогресс'


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'points', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('title', 'description')


@admin.register(LearningModule)
class LearningModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'difficulty', 'category', 'is_published', 'estimated_time')
    list_filter = ('difficulty', 'category', 'is_published')
    search_fields = ('title', 'description')


@admin.register(TeenChatSession)
class TeenChatSessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'user', 'title', 'created_at', 'updated_at')
    list_filter = ('created_at', 'user')
    search_fields = ('session_id', 'title', 'user__username')


@admin.register(ScamAlert)
class ScamAlertAdmin(admin.ModelAdmin):
    list_display = ('user', 'severity', 'risk_score', 'is_suspicious', 'created_at')
    list_filter = ('severity', 'is_suspicious', 'created_at')
    search_fields = ('user__username', 'reported_text')

