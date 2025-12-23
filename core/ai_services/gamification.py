"""
Gamification Service for Teen FinTech Platform
Handles achievements, streaks, badges, and engagement mechanics
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta, date
from dataclasses import dataclass

from django.contrib.auth.models import User
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone

from ..models import (
    Achievement, UserAchievement, UserProfile, 
    UserGoal, UserProgress, LearningModule, Quiz, UserQuizAttempt,
    Income, Expense, TeenChatSession, ScamAlert
)

logger = logging.getLogger(__name__)


@dataclass
class AchievementCheck:
    """Result of achievement checking"""
    unlocked: bool
    achievement: Achievement
    progress: Dict[str, Any]
    points_awarded: int
    message: str


class GamificationEngine:
    """
    Core gamification engine that manages achievements, streaks, and user engagement
    """
    
    def __init__(self):
        self.achievement_templates = self._load_achievement_templates()
        
    def _load_achievement_templates(self) -> List[Dict]:
        """Load predefined achievement templates"""
        return [
            # First Steps Achievements
            {
                'title': 'Первые шаги',
                'description': 'Зарегистрировался в приложении и начал свой финансовый путь',
                'category': 'milestone',
                'icon': '🚀',
                'criteria': {'type': 'registration'},
                'points': 10,
                'iq_bonus': 1
            },
            {
                'title': 'Первая цель',
                'description': 'Поставил свою первую финансовую цель',
                'category': 'goal',
                'icon': '🎯',
                'criteria': {'type': 'first_goal_created'},
                'points': 15,
                'iq_bonus': 2
            },
            {
                'title': 'Первый бюджет',
                'description': 'Создал свой первый месячный бюджет',
                'category': 'budgeting',
                'icon': '📊',
                'criteria': {'type': 'first_budget_created'},
                'points': 15,
                'iq_bonus': 2
            },
            
            # Learning Achievements
            {
                'title': 'Ученик',
                'description': 'Завершил первый урок по финансовой грамотности',
                'category': 'learning',
                'icon': '📚',
                'criteria': {'type': 'lessons_completed', 'value': 1},
                'points': 20,
                'iq_bonus': 3
            },
            {
                'title': 'Знаток',
                'description': 'Завершил 5 уроков по финансовой грамотности',
                'category': 'learning',
                'icon': '🧠',
                'criteria': {'type': 'lessons_completed', 'value': 5},
                'points': 50,
                'iq_bonus': 5
            },
            {
                'title': 'Эксперт',
                'description': 'Завершил 10 уроков и стал настоящим экспертом',
                'category': 'learning',
                'icon': '🏆',
                'criteria': {'type': 'lessons_completed', 'value': 10},
                'points': 100,
                'iq_bonus': 10
            },
            {
                'title': 'Отличник',
                'description': 'Успешно прошел 5 квизов',
                'category': 'learning',
                'icon': '⭐',
                'criteria': {'type': 'quizzes_passed', 'value': 5},
                'points': 40,
                'iq_bonus': 4
            },
            
            # Goal Achievement
            {
                'title': 'Мечтатель',
                'description': 'Поставил цель накопить на что-то важное',
                'category': 'goal',
                'icon': '💭',
                'criteria': {'type': 'goals_created', 'value': 1},
                'points': 15,
                'iq_bonus': 2
            },
            {
                'title': 'Накопитель',
                'description': 'Накопил 50% от цели',
                'category': 'saving',
                'icon': '💰',
                'criteria': {'type': 'goal_progress', 'value': 50},
                'points': 30,
                'iq_bonus': 3
            },
            {
                'title': 'Достигатор',
                'description': 'Достиг своей первой финансовой цели',
                'category': 'goal',
                'icon': '🎉',
                'criteria': {'type': 'goals_achieved', 'value': 1},
                'points': 75,
                'iq_bonus': 8
            },
            {
                'title': 'Чемпион целей',
                'description': 'Достиг 5 финансовых целей',
                'category': 'goal',
                'icon': '👑',
                'criteria': {'type': 'goals_achieved', 'value': 5},
                'points': 150,
                'iq_bonus': 15
            },
            
            # Budgeting Mastery
            {
                'title': 'Бюджетный мастер',
                'description': 'Ведешь бюджет 7 дней подряд',
                'category': 'budgeting',
                'icon': '📋',
                'criteria': {'type': 'budget_streak', 'value': 7},
                'points': 40,
                'iq_bonus': 4
            },
            {
                'title': 'Экономист',
                'description': 'Успешно уложился в бюджет 3 месяца подряд',
                'category': 'budgeting',
                'icon': '💡',
                'criteria': {'type': 'budget_success_streak', 'value': 3},
                'points': 80,
                'iq_bonus': 8
            },
            
            # AI Coach Engagement
            {
                'title': 'Первый разговор',
                'description': 'Провел первую беседу с AI финансовым коучем',
                'category': 'learning',
                'icon': '💬',
                'criteria': {'type': 'first_ai_chat'},
                'points': 25,
                'iq_bonus': 3
            },
            {
                'title': 'Любознательный',
                'description': 'Задал 10 вопросов AI коучу',
                'category': 'learning',
                'icon': '🤔',
                'criteria': {'type': 'ai_chats', 'value': 10},
                'points': 50,
                'iq_bonus': 5
            },
            {
                'title': 'Постоянный ученик',
                'description': 'Общался с AI коучем 30 дней подряд',
                'category': 'streak',
                'icon': '📖',
                'criteria': {'type': 'ai_chat_streak', 'value': 30},
                'points': 100,
                'iq_bonus': 10
            },
            
            # Smart Spending
            {
                'title': 'Умный покупатель',
                'description': 'Потратил меньше запланированного 5 раз',
                'category': 'saving',
                'icon': '🛒',
                'criteria': {'type': 'under_budget_count', 'value': 5},
                'points': 35,
                'iq_bonus': 4
            },
            {
                'title': 'Транжира-исправитель',
                'description': 'Сократил траты на развлечения на 20%',
                'category': 'saving',
                'icon': '🎮➡️📚',
                'criteria': {'type': 'entertainment_reduction', 'value': 20},
                'points': 60,
                'iq_bonus': 6
            },
            
            # Security & Safety
            {
                'title': 'Защитник',
                'description': 'Использовал модуль защиты от мошенничества',
                'category': 'security',
                'icon': '🛡️',
                'criteria': {'type': 'scam_checks', 'value': 1},
                'points': 30,
                'iq_bonus': 3
            },
            {
                'title': 'Анти-скам герой',
                'description': 'Выявил 5 подозрительных предложений',
                'category': 'security',
                'icon': '🦸‍♂️',
                'criteria': {'type': 'scams_identified', 'value': 5},
                'points': 75,
                'iq_bonus': 8
            },
            
            # Streak Achievements
            {
                'title': 'Постоянство',
                'description': 'Заходил в приложение 7 дней подряд',
                'category': 'streak',
                'icon': '🔥',
                'criteria': {'type': 'login_streak', 'value': 7},
                'points': 25,
                'iq_bonus': 3
            },
            {
                'title': 'Привычка',
                'description': 'Заходил в приложение 30 дней подряд',
                'category': 'streak',
                'icon': '💪',
                'criteria': {'type': 'login_streak', 'value': 30},
                'points': 100,
                'iq_bonus': 10
            },
            {
                'title': 'Неукротимый',
                'description': 'Заходил в приложение 100 дней подряд',
                'category': 'streak',
                'icon': '⚡',
                'criteria': {'type': 'login_streak', 'value': 100},
                'points': 250,
                'iq_bonus': 25
            },
            
            # Special Achievements
            {
                'title': 'Финансовый гений',
                'description': 'Достиг максимального уровня Financial IQ (100)',
                'category': 'learning',
                'icon': '🧠💎',
                'criteria': {'type': 'financial_iq', 'value': 100},
                'points': 200,
                'iq_bonus': 20
            },
            {
                'title': 'Мастер финансов',
                'description': 'Получил все основные достижения',
                'category': 'milestone',
                'icon': '🏅',
                'criteria': {'type': 'all_achievements'},
                'points': 500,
                'iq_bonus': 50
            }
        ]
    
    def initialize_achievements(self):
        """Initialize achievement templates in database"""
        for template in self.achievement_templates:
            Achievement.objects.get_or_create(
                title=template['title'],
                defaults={
                    'description': template['description'],
                    'category': template['category'],
                    'icon': template['icon'],
                    'criteria': template['criteria'],
                    'points': template['points'],
                    'iq_bonus': template['iq_bonus']
                }
            )
    
    def check_user_achievements(self, user: User) -> List[AchievementCheck]:
        """Check which achievements user has unlocked"""
        try:
            profile = user.teen_profile
            progress = user.progress
            
            unlocked_achievements = []
            existing_user_achievements = set(
                UserAchievement.objects.filter(user=user).values_list('achievement_id', flat=True)
            )
            
            for achievement in Achievement.objects.filter(is_active=True):
                if achievement.id in existing_user_achievements:
                    continue
                
                check_result = self._check_single_achievement(user, achievement)
                if check_result.unlocked:
                    unlocked_achievements.append(check_result)
            
            return unlocked_achievements
            
        except Exception as e:
            logger.error(f"Error checking achievements for user {user.id}: {e}")
            return []
    
    def _check_single_achievement(self, user: User, achievement: Achievement) -> AchievementCheck:
        """Check if user has unlocked a specific achievement"""
        try:
            criteria = achievement.criteria
            criteria_type = criteria.get('type')
            required_value = criteria.get('value', 1)
            
            progress_data = {}
            
            if criteria_type == 'registration':
                # Always true for registered users
                return AchievementCheck(
                    unlocked=True,
                    achievement=achievement,
                    progress={'registration_date': user.date_joined},
                    points_awarded=achievement.points,
                    message=f"Поздравляем! Вы получили достижение '{achievement.title}'!"
                )
            
            elif criteria_type == 'lessons_completed':
                completed = user.teen_profile.lessons_completed
                progress_data = {'lessons_completed': completed}
                unlocked = completed >= required_value
                
            elif criteria_type == 'quizzes_passed':
                passed = user.teen_profile.quizzes_passed
                progress_data = {'quizzes_passed': passed}
                unlocked = passed >= required_value
                
            elif criteria_type == 'goals_created':
                created = user.goals.count()
                progress_data = {'goals_created': created}
                unlocked = created >= required_value
                
            elif criteria_type == 'goals_achieved':
                achieved = user.teen_profile.goals_achieved
                progress_data = {'goals_achieved': achieved}
                unlocked = achieved >= required_value
                
            elif criteria_type == 'goal_progress':
                # Check if any goal has reached the progress threshold
                max_progress = max([goal.progress_percentage() for goal in user.goals.all()], default=0)
                progress_data = {'max_goal_progress': max_progress}
                unlocked = max_progress >= required_value
                
            elif criteria_type == 'financial_iq':
                iq_score = user.teen_profile.financial_iq_score
                progress_data = {'financial_iq': iq_score}
                unlocked = iq_score >= required_value
                
            elif criteria_type == 'ai_chats':
                chats = user.teen_chat_sessions.count()
                progress_data = {'ai_chats': chats}
                unlocked = chats >= required_value
                
            elif criteria_type == 'first_ai_chat':
                unlocked = user.teen_chat_sessions.exists()
                progress_data = {'first_chat_date': user.teen_chat_sessions.first().created_at if unlocked else None}
                
            elif criteria_type == 'scam_checks':
                checks = ScamAlert.objects.filter(user=user).count()
                progress_data = {'scam_checks': checks}
                unlocked = checks >= required_value
                
            elif criteria_type == 'scams_identified':
                identified = ScamAlert.objects.filter(user=user, is_suspicious=True).count()
                progress_data = {'scams_identified': identified}
                unlocked = identified >= required_value
                
            elif criteria_type == 'login_streak':
                streak = self._calculate_login_streak(user)
                progress_data = {'current_streak': streak}
                unlocked = streak >= required_value
                
            elif criteria_type == 'budget_streak':
                streak = self._calculate_budget_streak(user)
                progress_data = {'budget_streak': streak}
                unlocked = streak >= required_value
                
            elif criteria_type == 'all_achievements':
                # Check if user has all major achievements
                major_achievements = Achievement.objects.filter(
                    category__in=['learning', 'goal', 'budgeting']
                ).count()
                user_major_achievements = UserAchievement.objects.filter(
                    user=user,
                    achievement__category__in=['learning', 'goal', 'budgeting']
                ).count()
                progress_data = {
                    'major_achievements': user_major_achievements,
                    'total_major': major_achievements
                }
                unlocked = user_major_achievements >= major_achievements * 0.8  # 80% threshold
                
            else:
                unlocked = False
            
            if unlocked:
                return AchievementCheck(
                    unlocked=True,
                    achievement=achievement,
                    progress=progress_data,
                    points_awarded=achievement.points,
                    message=f"Поздравляем! Вы получили достижение '{achievement.title}'!"
                )
            else:
                return AchievementCheck(
                    unlocked=False,
                    achievement=achievement,
                    progress=progress_data,
                    points_awarded=0,
                    message=""
                )
                
        except Exception as e:
            logger.error(f"Error checking achievement {achievement.title}: {e}")
            return AchievementCheck(
                unlocked=False,
                achievement=achievement,
                progress={},
                points_awarded=0,
                message=""
            )
    
    def unlock_achievements(self, user: User, achievements: List[AchievementCheck]) -> Dict[str, Any]:
        """Unlock achievements for user and update their profile"""
        try:
            newly_unlocked = []
            total_points = 0
            total_iq_bonus = 0
            
            for achievement_check in achievements:
                if achievement_check.unlocked:
                    # Create user achievement record
                    UserAchievement.objects.create(
                        user=user,
                        achievement=achievement_check.achievement,
                        progress=achievement_check.progress,
                        is_completed=True
                    )
                    
                    newly_unlocked.append({
                        'title': achievement_check.achievement.title,
                        'description': achievement_check.achievement.description,
                        'icon': achievement_check.achievement.icon,
                        'category': achievement_check.achievement.category,
                        'points': achievement_check.points_awarded,
                        'iq_bonus': achievement_check.achievement.iq_bonus,
                        'message': achievement_check.message
                    })
                    
                    total_points += achievement_check.points_awarded
                    total_iq_bonus += achievement_check.achievement.iq_bonus
            
            if total_points > 0:
                # Update user profile
                profile = user.teen_profile
                profile.total_achievements += len(newly_unlocked)
                profile.financial_iq_score = min(100, profile.financial_iq_score + total_iq_bonus)
                profile.save()
                
                # Update progress
                progress = user.progress
                progress.total_achievements = profile.total_achievements
                progress.save()
            
            return {
                'unlocked_count': len(newly_unlocked),
                'total_points': total_points,
                'total_iq_bonus': total_iq_bonus,
                'new_iq_score': user.teen_profile.financial_iq_score,
                'achievements': newly_unlocked
            }
            
        except Exception as e:
            logger.error(f"Error unlocking achievements for user {user.id}: {e}")
            return {'unlocked_count': 0, 'achievements': [], 'error': str(e)}
    
    def _calculate_login_streak(self, user: User) -> int:
        """Calculate current login streak for user"""
        try:
            # Get user's last activity
            progress = user.progress
            if not progress.last_activity:
                return 0
            
            last_activity = progress.last_activity.date()
            today = timezone.now().date()
            
            # Calculate days difference
            days_diff = (today - last_activity).days
            
            # If more than 1 day gap, streak is broken
            if days_diff > 1:
                return 0
            
            # If last activity was yesterday, continue streak
            if days_diff == 1:
                return progress.streak_days + 1
            
            # If last activity was today, keep current streak
            return progress.streak_days
            
        except Exception as e:
            logger.error(f"Error calculating login streak: {e}")
            return 0
    
    def _calculate_budget_streak(self, user: User) -> int:
        """Calculate streak of consecutive days with budget updates"""
        try:
            # This would require tracking daily budget updates
            # For now, return a simplified version
            recent_expenses = user.teen_expenses.filter(
                date__gte=timezone.now().date() - timedelta(days=30)
            ).values('date').distinct().count()
            
            return min(recent_expenses, 30)  # Max 30 days
            
        except Exception as e:
            logger.error(f"Error calculating budget streak: {e}")
            return 0
    
    def update_user_activity(self, user: User):
        """Update user activity and check for streak achievements"""
        try:
            progress = user.progress
            today = timezone.now().date()
            last_activity = progress.last_activity.date() if progress.last_activity else None
            
            if last_activity:
                days_diff = (today - last_activity).days
                
                if days_diff == 1:
                    # Continue streak
                    progress.streak_days += 1
                    progress.current_streak += 1
                elif days_diff == 0:
                    # Same day, don't change streak
                    pass
                else:
                    # Streak broken
                    progress.streak_days = 1
                    progress.current_streak = 1
            else:
                # First activity
                progress.streak_days = 1
                progress.current_streak = 1
            
            progress.last_activity = timezone.now()
            progress.save()
            
            # Update profile streak
            profile = user.teen_profile
            profile.current_streak = progress.current_streak
            if progress.current_streak > profile.longest_streak:
                profile.longest_streak = progress.current_streak
            profile.save()
            
        except Exception as e:
            logger.error(f"Error updating user activity: {e}")
    
    def get_user_dashboard_data(self, user: User) -> Dict[str, Any]:
        """Get gamification data for user dashboard"""
        try:
            profile = user.teen_profile
            progress = user.progress
            
            # Get user achievements
            user_achievements = UserAchievement.objects.filter(user=user).select_related('achievement')
            
            achievements_by_category = {}
            total_points = 0
            
            for user_achievement in user_achievements:
                category = user_achievement.achievement.category
                if category not in achievements_by_category:
                    achievements_by_category[category] = []
                
                achievements_by_category[category].append({
                    'title': user_achievement.achievement.title,
                    'description': user_achievement.achievement.description,
                    'icon': user_achievement.achievement.icon,
                    'earned_at': user_achievement.earned_at,
                    'points': user_achievement.achievement.points
                })
                
                total_points += user_achievement.achievement.points
            
            # Get available achievements (not yet earned)
            earned_achievement_ids = set(user_achievements.values_list('achievement_id', flat=True))
            available_achievements = Achievement.objects.filter(
                is_active=True
            ).exclude(
                id__in=earned_achievement_ids
            )[:5]  # Show top 5 available
            
            next_achievements = []
            for achievement in available_achievements:
                check_result = self._check_single_achievement(user, achievement)
                progress_percent = self._calculate_achievement_progress(check_result.progress, achievement.criteria)
                
                next_achievements.append({
                    'title': achievement.title,
                    'description': achievement.description,
                    'icon': achievement.icon,
                    'progress': progress_percent,
                    'points': achievement.points
                })
            
            return {
                'financial_iq_score': profile.financial_iq_score,
                'total_achievements': profile.total_achievements,
                'current_streak': profile.current_streak,
                'longest_streak': profile.longest_streak,
                'total_points': total_points,
                'earned_achievements': achievements_by_category,
                'next_achievements': next_achievements,
                'level': self._calculate_user_level(total_points),
                'progress_to_next_level': self._calculate_progress_to_next_level(total_points)
            }
            
        except Exception as e:
            logger.error(f"Error getting user dashboard data: {e}")
            return {}
    
    def _calculate_achievement_progress(self, progress_data: Dict, criteria: Dict) -> int:
        """Calculate progress percentage toward achievement"""
        try:
            criteria_type = criteria.get('type')
            required_value = criteria.get('value', 1)
            
            if criteria_type == 'lessons_completed':
                current = progress_data.get('lessons_completed', 0)
            elif criteria_type == 'quizzes_passed':
                current = progress_data.get('quizzes_passed', 0)
            elif criteria_type == 'goals_created':
                current = progress_data.get('goals_created', 0)
            elif criteria_type == 'goals_achieved':
                current = progress_data.get('goals_achieved', 0)
            elif criteria_type == 'goal_progress':
                current = progress_data.get('max_goal_progress', 0)
            elif criteria_type == 'financial_iq':
                current = progress_data.get('financial_iq', 0)
            elif criteria_type == 'ai_chats':
                current = progress_data.get('ai_chats', 0)
            elif criteria_type == 'scam_checks':
                current = progress_data.get('scam_checks', 0)
            elif criteria_type == 'scams_identified':
                current = progress_data.get('scams_identified', 0)
            elif criteria_type == 'login_streak':
                current = progress_data.get('current_streak', 0)
            elif criteria_type == 'budget_streak':
                current = progress_data.get('budget_streak', 0)
            else:
                return 0
            
            return min(100, int((current / required_value) * 100))
            
        except Exception as e:
            logger.error(f"Error calculating achievement progress: {e}")
            return 0
    
    def _calculate_user_level(self, total_points: int) -> int:
        """Calculate user level based on total points"""
        # Level calculation: Every 100 points = 1 level
        return max(1, (total_points // 100) + 1)
    
    def _calculate_progress_to_next_level(self, total_points: int) -> Dict[str, int]:
        """Calculate progress to next level"""
        current_level = self._calculate_user_level(total_points)
        current_level_points = (current_level - 1) * 100
        next_level_points = current_level * 100
        
        progress_points = total_points - current_level_points
        needed_points = next_level_points - current_level_points
        
        return {
            'current': progress_points,
            'needed': needed_points,
            'percentage': int((progress_points / needed_points) * 100) if needed_points > 0 else 100
        }


# Global gamification engine instance
gamification_engine = GamificationEngine()