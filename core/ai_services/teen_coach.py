"""
Teen Financial Coach AI Service
Provides age-appropriate financial guidance and education for teens
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.db.models import Q, Sum, Count
from .llm_manager import llm_manager, LLMResponse
from ..models import (
    UserGoal, Income, Expense, UserProfile, 
    TeenChatSession, TeenChatMessage, LearningModule,
    Achievement, UserAchievement
)

logger = logging.getLogger(__name__)


class TeenFinancialCoach:
    """
    AI-powered financial coach specifically designed for teenagers
    Provides personalized guidance on budgeting, saving, and financial literacy
    """
    
    def __init__(self):
        self.llm = llm_manager
        
    async def get_coaching_response(self, 
                                  user: User,
                                  message: str,
                                  context: Dict = None) -> Dict[str, Any]:
        """
        Main coaching method - processes user message and returns AI response
        """
        try:
            # Get user profile and context
            profile = user.teen_profile
            user_context = await self._build_user_context(user)
            
            # Build conversation history
            conversation_history = await self._get_conversation_history(user)
            
            # Create system prompt for teen coaching
            system_prompt = self._create_coaching_system_prompt(profile, user_context)
            
            # Prepare messages for LLM
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add recent conversation history
            messages.extend(conversation_history[-6:])  # Last 3 exchanges
            
            # Add current user message
            messages.append({"role": "user", "content": message})
            
            # Get AI response
            response = await self.llm.chat(messages, temperature=0.7, max_tokens=800)
            
            # Analyze response for educational content
            educational_analysis = await self._analyze_educational_content(response.content, message)
            
            # Save interaction to database
            chat_session = await self._save_chat_interaction(
                user, message, response, educational_analysis
            )
            
            # Check for achievements
            await self._check_coaching_achievements(user, message, response.content)
            
            return {
                'response': response.content,
                'session_id': chat_session.session_id,
                'confidence': response.confidence,
                'educational_content': educational_analysis.get('contains_educational', False),
                'learning_objective': educational_analysis.get('objective'),
                'reasoning_explained': educational_analysis.get('reasoning'),
                'was_actionable': educational_analysis.get('actionable', False),
                'ai_reasoning': await self._generate_reasoning(response.content, user_context)
            }
            
        except Exception as e:
            logger.error(f"Error in teen coaching: {e}")
            return {
                'response': "Извините, произошла техническая ошибка. Попробуйте позже.",
                'error': str(e)
            }
    
    def _create_coaching_system_prompt(self, profile: UserProfile, user_context: Dict) -> str:
        """Create system prompt tailored to specific teen user"""
        
        age = profile.age or 16  # Default to 16 if not set
        language = profile.preferred_language
        
        base_prompt = {
            'ru': f"""
Ты - персональный финансовый коуч для подростка {age} лет из Кыргызстана.
Твоя цель - помочь подростку научиться управлять деньгами и достигать финансовых целей.

ПРИНЦИПЫ РАБОТЫ:
- Говори простым языком, понятным {age}-летнему школьнику
- Всегда объясняй "почему" свои советы
- Используй примеры из жизни подростков в Кыргызстане
- Будь позитивным и мотивирующим
- Предлагай конкретные действия
- Помогай ставить реалистичные цели

ТЕКУЩАЯ СИТУАЦИЯ ПОЛЬЗОВАТЕЛЯ:
- Возраст: {age} лет
- Месячная сумма на расходы: {user_context.get('monthly_allowance', 0)} сом
- Активные цели: {user_context.get('active_goals', 0)}
- Недавние доходы: {user_context.get('recent_income', 0)} сом
- Недавние расходы: {user_context.get('recent_expenses', 0)} сом

ОБЛАСТИ ПОМОЩИ:
1. Планирование бюджета (карманные деньги, подработка)
2. Накопления на цели (телефон, ноутбук, курсы)
3. Экономия на развлечениях и покупках
4. Понимание стоимости денег
5. Безопасность в интернете и избегание мошенничества
6. Первые шаги в инвестировании

НЕ ГОВОРИ О:
- Взрослых финансовых продуктах (кредиты, ипотека)
- Сложных инвестиционных стратегиях
- Налогообложении
- Страховании

ОТВЕЧАЙ КОНКРЕТНО:
- Предлагай цифры и суммы в сомах
- Дай практические советы
- Объясни, как это поможет достичь цели
""",
            'en': f"""
You are a personal financial coach for a {age}-year-old teenager from Kyrgyzstan.
Your goal is to help the teenager learn to manage money and achieve financial goals.

WORKING PRINCIPLES:
- Speak in simple language that a {age}-year-old student can understand
- Always explain "why" your advice
- Use examples from teen life in Kyrgyzstan
- Be positive and motivating
- Offer concrete actions
- Help set realistic goals

USER'S CURRENT SITUATION:
- Age: {age} years
- Monthly allowance: {user_context.get('monthly_allowance', 0)} KGS
- Active goals: {user_context.get('active_goals', 0)}
- Recent income: {user_context.get('recent_income', 0)} KGS
- Recent expenses: {user_context.get('recent_expenses', 0)} KGS

AREAS OF HELP:
1. Budget planning (allowance, part-time work)
2. Saving for goals (phone, laptop, courses)
3. Saving on entertainment and purchases
4. Understanding the value of money
5. Internet safety and avoiding fraud
6. First steps in investing

DO NOT TALK ABOUT:
- Adult financial products (loans, mortgages)
- Complex investment strategies
- Taxation
- Insurance

BE SPECIFIC:
- Offer amounts in KGS
- Give practical advice
- Explain how this will help achieve the goal
"""
        }
        
        return base_prompt.get(language, base_prompt['ru'])
    
    async def _build_user_context(self, user: User) -> Dict[str, Any]:
        """Build comprehensive user context for AI coaching"""
        try:
            profile = user.teen_profile
            
            # Basic info
            context = {
                'age': profile.age or 16,
                'monthly_allowance': float(profile.monthly_allowance or 0),
                'currency': profile.currency,
                'preferred_language': profile.preferred_language,
                'financial_iq_score': profile.financial_iq_score
            }
            
            # Goals context
            active_goals = user.goals.filter(status='active')
            context['active_goals'] = active_goals.count()
            if active_goals.exists():
                goal = active_goals.first()
                context['primary_goal'] = {
                    'title': goal.title,
                    'target_amount': float(goal.target_amount),
                    'current_amount': float(goal.current_amount),
                    'progress': goal.progress_percentage(),
                    'days_remaining': goal.days_remaining()
                }
            
            # Recent financial activity (last 30 days)
            thirty_days_ago = datetime.now().date() - timedelta(days=30)
            recent_income = user.teen_incomes.filter(date__gte=thirty_days_ago).aggregate(
                total=Sum('amount')
            )['total'] or 0
            
            recent_expenses = user.teen_expenses.filter(date__gte=thirty_days_ago).aggregate(
                total=Sum('amount')
            )['total'] or 0
            
            context['recent_income'] = float(recent_income)
            context['recent_expenses'] = float(recent_expenses)
            context['net_flow'] = context['recent_income'] - context['recent_expenses']
            
            # Spending categories
            spending_categories = user.teen_expenses.filter(date__gte=thirty_days_ago).values(
                'expense_type'
            ).annotate(
                total=Sum('amount'),
                count=Count('id')
            ).order_by('-total')
            
            context['top_spending_categories'] = [
                {
                    'category': cat['expense_type'],
                    'amount': float(cat['total']),
                    'transactions': cat['count']
                }
                for cat in spending_categories[:3]
            ]
            
            # Learning progress
            context['lessons_completed'] = profile.lessons_completed
            context['quizzes_passed'] = profile.quizzes_passed
            context['achievements_count'] = profile.total_achievements
            
            return context
            
        except Exception as e:
            logger.error(f"Error building user context: {e}")
            return {'age': 16, 'monthly_allowance': 0, 'currency': 'KGS'}
    
    async def _get_conversation_history(self, user: User) -> List[Dict[str, str]]:
        """Get recent conversation history for context"""
        try:
            recent_sessions = user.teen_chat_sessions.order_by('-updated_at')[:2]
            history = []
            
            for session in recent_sessions:
                messages = session.teen_messages.order_by('created_at')[-6:]  # Last 3 exchanges
                for msg in messages:
                    if msg.role in ['user', 'teen_coach']:
                        history.append({
                            'role': msg.role,
                            'content': msg.content
                        })
            
            return history
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []
    
    async def _analyze_educational_content(self, response: str, user_message: str) -> Dict[str, Any]:
        """Analyze if response contains educational content"""
        educational_indicators = [
            'важно понимать', 'запомни', 'правило', 'совет', 'объясняю',
            'почему это важно', 'пример', 'подумай о том',
            'чтобы научиться', 'навык', 'умение'
        ]
        
        actionable_indicators = [
            'попробуй', 'начни с', 'сделай', 'поставь цель', 'считай',
            'запиши', 'план', 'шаг', 'действие', 'измени'
        ]
        
        response_lower = response.lower()
        message_lower = user_message.lower()
        
        contains_educational = any(indicator in response_lower for indicator in educational_indicators)
        is_actionable = any(indicator in response_lower for indicator in actionable_indicators)
        
        # Determine learning objective
        learning_objective = None
        if any(word in message_lower for word in ['как', 'как сэкономить', 'как накопить']):
            learning_objective = "Основы экономии и накоплений"
        elif any(word in message_lower for word in ['бюджет', 'планировать']):
            learning_objective = "Планирование бюджета"
        elif any(word in message_lower for word in ['цель', 'накопить на']):
            learning_objective = "Постановка и достижение финансовых целей"
        
        return {
            'contains_educational': contains_educational,
            'actionable': is_actionable,
            'objective': learning_objective,
            'educational_indicators_count': sum(1 for indicator in educational_indicators if indicator in response_lower),
            'actionable_indicators_count': sum(1 for indicator in actionable_indicators if indicator in response_lower)
        }
    
    async def _save_chat_interaction(self, 
                                   user: User, 
                                   user_message: str, 
                                   llm_response: LLMResponse,
                                   analysis: Dict) -> TeenChatSession:
        """Save chat interaction to database"""
        try:
            # Get or create current session
            session, created = TeenChatSession.objects.get_or_create(
                user=user,
                session_id=f"session_{user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                defaults={
                    'title': f"Coaching session - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    'conversation_context': analysis,
                    'coaching_focus': analysis.get('objective', 'General coaching')
                }
            )
            
            # Save user message
            TeenChatMessage.objects.create(
                session=session,
                role='user',
                content=user_message,
                is_educational=analysis.get('contains_educational', False),
                learning_objective=analysis.get('objective'),
                was_actionable=analysis.get('actionable', False)
            )
            
            # Save AI response
            TeenChatMessage.objects.create(
                session=session,
                role='teen_coach',
                content=llm_response.content,
                is_educational=analysis.get('contains_educational', False),
                learning_objective=analysis.get('objective'),
                confidence_score=llm_response.confidence,
                reasoning_explained=analysis.get('reasoning', ''),
                was_actionable=analysis.get('actionable', False)
            )
            
            return session
            
        except Exception as e:
            logger.error(f"Error saving chat interaction: {e}")
            raise
    
    async def _check_coaching_achievements(self, user: User, message: str, response: str):
        """Check if user unlocked any achievements through coaching"""
        try:
            # First coaching conversation achievement
            if not user.teen_chat_sessions.exists():
                achievement = Achievement.objects.get(title="Первый разговор с AI")
                UserAchievement.objects.get_or_create(
                    user=user,
                    achievement=achievement,
                    defaults={'is_completed': True}
                )
            
            # Ask about goals achievement
            if any(word in message.lower() for word in ['цель', 'накопить на', 'хочу купить']):
                achievement = Achievement.objects.get(title="Целеустремленный")
                UserAchievement.objects.get_or_create(
                    user=user,
                    achievement=achievement,
                    defaults={'is_completed': True}
                )
            
            # Ask about budgeting achievement
            if any(word in message.lower() for word in ['бюджет', 'планировать', 'тратить']):
                achievement = Achievement.objects.get(title="Планировщик бюджета")
                UserAchievement.objects.get_or_create(
                    user=user,
                    achievement=achievement,
                    defaults={'is_completed': True}
                )
                
        except Achievement.DoesNotExist:
            pass  # Achievement not created yet
        except Exception as e:
            logger.error(f"Error checking achievements: {e}")
    
    async def _generate_reasoning(self, response: str, user_context: Dict) -> str:
        """Generate explanation of AI reasoning for transparency"""
        try:
            reasoning_prompt = {
                'ru': f"""
Объясни кратко, почему ты дал такой совет этому подростку.
Учти его возраст, финансовую ситуацию и цели.
Ответь 1-2 предложениями простыми словами.""",
                'en': f"""
Explain briefly why you gave this advice to this teenager.
Consider his age, financial situation, and goals.
Answer in 1-2 simple sentences."""
            }
            
            messages = [
                {"role": "system", "content": reasoning_prompt.get('ru', reasoning_prompt['ru'])},
                {"role": "user", "content": f"Context: {json.dumps(user_context, ensure_ascii=False)}\n\nAI Response: {response}\n\nWhy did you give this advice?"}
            ]
            
            reasoning_response = await self.llm.chat(messages, temperature=0.3, max_tokens=200)
            return reasoning_response.content
            
        except Exception as e:
            logger.error(f"Error generating reasoning: {e}")
            return "Совет основан на твоей текущей финансовой ситуации и целях."
    
    async def get_personalized_savings_advice(self, user: User, goal: UserGoal) -> Dict[str, Any]:
        """Get specific savings advice for a particular goal"""
        try:
            profile = user.teen_profile
            context = await self._build_user_context(user)
            
            # Add goal-specific context
            goal_context = context.copy()
            goal_context['specific_goal'] = {
                'title': goal.title,
                'target_amount': float(goal.target_amount),
                'current_amount': float(goal.current_amount),
                'progress': goal.progress_percentage(),
                'target_date': goal.target_date.isoformat(),
                'days_remaining': goal.days_remaining()
            }
            
            system_prompt = self._create_coaching_system_prompt(profile, goal_context)
            
            savings_question = f"""
Помоги подростку накопить на цель: {goal.title}
Нужно накопить {goal.target_amount} сом к {goal.target_date.strftime('%d.%m.%Y')}
Сейчас накоплено: {goal.current_amount} сом
Рекомендуемая сумма в неделю: {goal.weekly_target():.0f} сом

Дай конкретные советы:
1. Сколько откладывать каждую неделю
2. На чем можно сэкономить
3. Как увеличить доходы (подработка)
4. Мотивационные советы
"""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": savings_question}
            ]
            
            response = await self.llm.chat(messages, temperature=0.6, max_tokens=600)
            
            return {
                'advice': response.content,
                'weekly_target': goal.weekly_target(),
                'confidence': response.confidence,
                'goal_progress': goal.progress_percentage()
            }
            
        except Exception as e:
            logger.error(f"Error getting savings advice: {e}")
            return {
                'advice': "Попробуй откладывать понемногу каждую неделю. Даже 100 сом в неделю помогут!",
                'weekly_target': 0,
                'confidence': 50
            }
    
    async def analyze_spending_patterns(self, user: User, days: int = 30) -> Dict[str, Any]:
        """Analyze user's spending patterns and provide insights"""
        try:
            context = await self._build_user_context(user)
            
            # Get spending data
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            
            expenses = user.teen_expenses.filter(date__gte=start_date, date__lte=end_date)
            
            if not expenses.exists():
                return {'message': 'Пока нет данных для анализа. Начни записывать расходы!'}
            
            # Analyze patterns
            total_spent = float(expenses.aggregate(total=Sum('amount'))['total'] or 0)
            
            by_category = expenses.values('expense_type').annotate(
                total=Sum('amount'),
                count=Count('id')
            ).order_by('-total')
            
            category_analysis = []
            for cat in by_category:
                percentage = (cat['total'] / total_spent) * 100 if total_spent > 0 else 0
                category_analysis.append({
                    'category': cat['expense_type'],
                    'amount': float(cat['total']),
                    'percentage': percentage,
                    'transactions': cat['count']
                })
            
            # Generate AI insights
            profile = user.teen_profile
            system_prompt = self._create_coaching_system_prompt(profile, context)
            
            analysis_prompt = f"""
Проанализируй расходы подростка за последние {days} дней:

Общая сумма: {total_spent} сом
По категориям: {json.dumps(category_analysis, ensure_ascii=False, indent=2)}

Дай 3 конкретных совета:
1. Где можно сократить расходы
2. Что можно изменить в привычках
3. Позитивные изменения в тратах
"""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": analysis_prompt}
            ]
            
            response = await self.llm.chat(messages, temperature=0.5, max_tokens=400)
            
            return {
                'total_spent': total_spent,
                'days_analyzed': days,
                'category_breakdown': category_analysis,
                'ai_insights': response.content,
                'average_daily': total_spent / days if days > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error analyzing spending patterns: {e}")
            return {'error': str(e)}


# Global teen coach instance
teen_coach = TeenFinancialCoach()