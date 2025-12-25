"""
Teen-focused views for FinBilim 2025 hackathon MVP
Modern, gamified interface for high school students
"""

import json
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Any

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone

from .models import (
    UserProfile, UserGoal, Income, Expense, TeenChatSession, TeenChatMessage,
    LearningModule, Quiz, QuizQuestion, UserQuizAttempt,
    Achievement, UserAchievement, FinancialInsight, ScamAlert, UserProgress
)
from .ai_services.teen_coach import teen_coach
from .ai_services.gamification import gamification_engine
from .ai_services.llm_manager import llm_manager

logger = logging.getLogger(__name__)


@login_required
def teen_dashboard(request):
    """
    Main teen dashboard with modern, gamified interface
    """
    try:
        user = request.user
        
        # Ensure profile exists
        if not hasattr(user, 'teen_profile'):
            UserProfile.objects.get_or_create(user=user)
        profile = user.teen_profile
        
        # Ensure progress exists (crucial for gamification engine)
        if not hasattr(user, 'progress'):
            UserProgress.objects.get_or_create(user=user)
        
        # Get gamification data
        gamification_data = gamification_engine.get_user_dashboard_data(user)
        
        # Get recent goals
        recent_goals = user.goals.filter(status='active')[:3]
        
        # Get recent spending insights
        recent_insights = user.financial_insights.filter(is_read=False)[:3]
        
        # Get active learning modules
        learning_modules = LearningModule.objects.filter(
            is_published=True
        ).order_by('difficulty', 'created_at')[:4]
        
        # Calculate today's spending
        today = date.today()
        today_expenses = user.teen_expenses.filter(date=today).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # Calculate this week's spending
        week_start = today - timedelta(days=today.weekday())
        week_expenses = user.teen_expenses.filter(
            date__gte=week_start
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Get AI coach chat sessions
        recent_chats = user.teen_chat_sessions.order_by('-updated_at')[:2]
        
        # Demo mode data
        demo_data = get_demo_data() if profile.demo_mode else None
        
        context = {
            'user': user,
            'profile': profile,
            'gamification': gamification_data,
            'recent_goals': recent_goals,
            'recent_insights': recent_insights,
            'learning_modules': learning_modules,
            'today_expenses': float(today_expenses),
            'week_expenses': float(week_expenses),
            'recent_chats': recent_chats,
            'demo_data': demo_data,
            'current_date': today,
        }
        
        return render(request, 'teen/dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Error in teen dashboard: {e}")
        messages.error(request, f"Ошибка загрузки подросткового раздела: {e}")
        return redirect('core:dashboard')  # Редирект на основной дашборд с графиками


@login_required
def goals_view(request):
    """
    Goals management page with progress visualization
    """
    try:
        user = request.user
        
        # Get all user goals
        goals = user.goals.all().order_by('-created_at')
        
        # Categorize goals
        active_goals = goals.filter(status='active')
        completed_goals = goals.filter(status='completed')
        
        # Calculate total saved amount
        total_saved = sum([float(goal.current_amount) for goal in active_goals])
        
        # Get gamification data for goals
        goal_achievements = UserAchievement.objects.filter(
            user=user,
            achievement__category='goal'
        ).select_related('achievement')
        
        context = {
            'active_goals': active_goals,
            'completed_goals': completed_goals,
            'total_saved': total_saved,
            'goal_achievements': goal_achievements,
        }
        
        return render(request, 'teen/goals.html', context)
        
    except Exception as e:
        logger.error(f"Error in goals view: {e}")
        messages.error(request, "Произошла ошибка при загрузке целей")
        return redirect('core:dashboard')


@login_required
def create_goal(request):
    """
    Create new savings goal with AI-powered suggestions
    """
    if request.method == 'POST':
        try:
            user = request.user
            
            # Extract form data
            title = request.POST.get('title', '').strip()
            description = request.POST.get('description', '').strip()
            target_amount = float(request.POST.get('target_amount', 0))
            category = request.POST.get('category', 'other')
            target_date_str = request.POST.get('target_date', '')
            
            if not title or target_amount <= 0 or not target_date_str:
                messages.error(request, "Заполните все обязательные поля")
                return redirect('core:goals')
            
            # Parse target date
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
            
            # Create goal
            goal = UserGoal.objects.create(
                user=user,
                title=title,
                description=description,
                target_amount=target_amount,
                category=category,
                target_date=target_date,
                weekly_saving_suggestion=0  # Will be calculated by AI
            )
            
            # Get AI recommendation
            try:
                ai_advice = teen_coach.get_personalized_savings_advice(user, goal)
                goal.ai_recommendation = ai_advice.get('advice', '')
                goal.weekly_saving_suggestion = ai_advice.get('weekly_target', 0)
                goal.save()
            except Exception as e:
                logger.error(f"Error getting AI advice for goal: {e}")
            
            # Update user progress
            progress = user.progress
            progress.goals_created += 1
            progress.last_goal_update = timezone.now()
            progress.save()
            
            # Check for achievements
            achievements = gamification_engine.check_user_achievements(user)
            if achievements:
                gamification_engine.unlock_achievements(user, achievements)
                messages.success(request, "🎉 Поздравляем! Вы получили новое достижение!")
            
            messages.success(request, f"Цель '{title}' создана успешно!")
            return redirect('core:goals')
            
        except ValueError:
            messages.error(request, "Некорректная сумма или дата")
            return redirect('core:goals')
        except Exception as e:
            logger.error(f"Error creating goal: {e}")
            messages.error(request, "Произошла ошибка при создании цели")
            return redirect('core:goals')
    
    return redirect('core:goals')


@login_required
def update_goal_progress(request, goal_id):
    """
    Update progress on a savings goal
    """
    if request.method == 'POST':
        try:
            user = request.user
            goal = get_object_or_404(UserGoal, id=goal_id, user=user)
            
            new_amount = float(request.POST.get('current_amount', 0))
            
            if new_amount < 0:
                messages.error(request, "Сумма не может быть отрицательной")
                return redirect('core:goals')
            
            # Update goal
            goal.current_amount = new_amount
            goal.save()
            
            # Check if goal is completed
            if goal.progress_percentage() >= 100 and goal.status == 'active':
                goal.status = 'completed'
                goal.completed_at = timezone.now()
                goal.save()
                
                # Update user profile
                profile = user.teen_profile
                profile.goals_achieved += 1
                profile.save()
                
                # Update progress
                progress = user.progress
                progress.goals_achieved += 1
                progress.save()
                
                messages.success(request, "🎉 Поздравляем! Вы достигли своей цели!")
            else:
                messages.success(request, "Прогресс обновлен!")
            
            # Check for achievements
            achievements = gamification_engine.check_user_achievements(user)
            if achievements:
                unlocked = gamification_engine.unlock_achievements(user, achievements)
                if unlocked['unlocked_count'] > 0:
                    messages.success(request, "🏆 Получено новое достижение!")
            
            return redirect('core:goals')
            
        except ValueError:
            messages.error(request, "Некорректная сумма")
            return redirect('core:goals')
        except Exception as e:
            logger.error(f"Error updating goal progress: {e}")
            messages.error(request, "Произошла ошибка при обновлении прогресса")
            return redirect('core:goals')
    
    return redirect('core:goals')


@login_required
def ai_coach(request):
    """
    AI Financial Coach chat interface
    """
    try:
        user = request.user
        profile = user.teen_profile
        
        # Get recent chat sessions
        chat_sessions = user.teen_chat_sessions.order_by('-updated_at')[:10]
        
        # Get current session if specified
        current_session_id = request.GET.get('session')
        current_session = None
        
        if current_session_id:
            current_session = get_object_or_404(
                TeenChatSession, 
                session_id=current_session_id, 
                user=user
            )
            messages = current_session.teen_messages.order_by('created_at')
        else:
            messages = []
        
        context = {
            'chat_sessions': chat_sessions,
            'current_session': current_session,
            'messages': messages,
            'user_age': profile.age or 16,
            'preferred_language': profile.preferred_language,
        }
        
        return render(request, 'teen/ai_coach.html', context)
        
    except Exception as e:
        logger.error(f"Error in AI coach view: {e}")
        messages.error(request, "Произошла ошибка при загрузке AI коуча")
        return redirect('core:dashboard')


@csrf_exempt
@login_required
def chat_with_ai(request):
    """
    Handle chat with AI financial coach
    """
    if request.method == 'POST':
        try:
            user = request.user
            data = json.loads(request.body)
            
            message = data.get('message', '').strip()
            session_id = data.get('session_id')
            
            if not message:
                return JsonResponse({'error': 'Сообщение не может быть пустым'}, status=400)
            
            # Get or create chat session
            if session_id:
                session = get_object_or_404(TeenChatSession, session_id=session_id, user=user)
            else:
                session = TeenChatSession.objects.create(
                    user=user,
                    session_id=f"session_{user.id}_{int(timezone.now().timestamp())}",
                    title=f"Chat - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                )
            
            # Get AI response
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                ai_response_data = loop.run_until_complete(
                    teen_coach.get_coaching_response(user, message)
                )
            finally:
                loop.close()
            
            # Save user message
            TeenChatMessage.objects.create(
                session=session,
                role='user',
                content=message
            )
            
            # Save AI response
            TeenChatMessage.objects.create(
                session=session,
                role='teen_coach',
                content=ai_response_data.get('response', 'Извините, произошла ошибка.'),
                confidence_score=ai_response_data.get('confidence'),
                reasoning_explained=ai_response_data.get('ai_reasoning'),
                is_educational=ai_response_data.get('educational_content', False),
                learning_objective=ai_response_data.get('learning_objective'),
                was_actionable=ai_response_data.get('was_actionable', False)
            )
            
            # Update user progress
            progress = user.progress
            progress.ai_conversations += 1
            progress.last_activity = timezone.now()
            progress.save()
            
            # Update user activity for streaks
            gamification_engine.update_user_activity(user)
            
            # Check for achievements
            achievements = gamification_engine.check_user_achievements(user)
            if achievements:
                unlocked = gamification_engine.unlock_achievements(user, achievements)
                
            return JsonResponse({
                'response': ai_response_data.get('response'),
                'session_id': session.session_id,
                'confidence': ai_response_data.get('confidence'),
                'educational': ai_response_data.get('educational_content', False),
                'actionable': ai_response_data.get('was_actionable', False),
                'reasoning': ai_response_data.get('ai_reasoning'),
                'achievements_unlocked': unlocked.get('unlocked_count', 0) if achievements else 0
            })
            
        except Exception as e:
            logger.error(f"Error in chat with AI: {e}")
            return JsonResponse({'error': 'Произошла ошибка при обработке сообщения'}, status=500)
    
    return JsonResponse({'error': 'Метод не поддерживается'}, status=405)


@login_required
def learning_modules(request):
    """
    Learning modules and educational content
    """
    try:
        # Get published modules
        modules = LearningModule.objects.filter(is_published=True).order_by('difficulty', 'created_at')
        
        # Get user's learning progress
        user_progress = {}
        for module in modules:
            attempts = UserQuizAttempt.objects.filter(user=request.user, quiz__module=module)
            user_progress[module.id] = {
                'attempts': attempts.count(),
                'best_score': attempts.aggregate(max_score=Max('score'))['max_score'] or 0,
                'passed': attempts.filter(passed=True).exists()
            }
        
        context = {
            'modules': modules,
            'user_progress': user_progress,
        }
        
        return render(request, 'teen/learning.html', context)
        
    except Exception as e:
        logger.error(f"Error in learning modules: {e}")
        messages.error(request, "Произошла ошибка при загрузке обучающих материалов")
        return redirect('core:dashboard')


@login_required
def module_detail(request, module_id):
    """
    Individual learning module view
    """
    try:
        module = get_object_or_404(LearningModule, id=module_id, is_published=True)
        
        # Get associated quiz
        quiz = module.quizzes.first()
        quiz_data = None
        
        if quiz:
            questions = quiz.questions.order_by('order')
            quiz_data = {
                'quiz': quiz,
                'questions': questions,
                'questions_count': questions.count()
            }
        
        # Get user's attempts for this module
        user_attempts = []
        if quiz:
            user_attempts = UserQuizAttempt.objects.filter(
                user=request.user,
                quiz=quiz
            ).order_by('-completed_at')
        
        context = {
            'module': module,
            'quiz_data': quiz_data,
            'user_attempts': user_attempts,
        }
        
        return render(request, 'teen/module_detail.html', context)
        
    except Exception as e:
        logger.error(f"Error in module detail: {e}")
        messages.error(request, "Произошла ошибка при загрузке урока")
        return redirect('core:learning')


@login_required
def take_quiz(request, quiz_id):
    """
    Take a quiz for a learning module
    """
    try:
        quiz = get_object_or_404(Quiz, id=quiz_id)
        questions = quiz.questions.order_by('order')
        
        if request.method == 'POST':
            # Process quiz answers
            correct_answers = 0
            total_questions = questions.count()
            answers_data = {}
            
            for question in questions:
                user_answer = request.POST.get(f'question_{question.id}', '')
                correct_answer = question.correct_answer
                
                is_correct = user_answer.lower() == correct_answer.lower()
                if is_correct:
                    correct_answers += 1
                
                answers_data[question.id] = {
                    'user_answer': user_answer,
                    'correct_answer': correct_answer,
                    'is_correct': is_correct
                }
            
            # Calculate score
            score = int((correct_answers / total_questions) * 100) if total_questions > 0 else 0
            passed = score >= quiz.passing_score
            
            # Save attempt
            attempt = UserQuizAttempt.objects.create(
                user=request.user,
                quiz=quiz,
                score=score,
                passed=passed,
                answers=answers_data
            )
            
            # Update user progress
            profile = request.user.teen_profile
            if passed:
                profile.quizzes_passed += 1
            profile.lessons_completed += 1
            profile.save()
            
            progress = request.user.progress
            progress.modules_completed += 1
            progress.last_lesson_date = timezone.now()
            progress.save()
            
            # Check for achievements
            achievements = gamification_engine.check_user_achievements(request.user)
            if achievements:
                unlocked = gamification_engine.unlock_achievements(request.user, achievements)
            
            # Calculate score for Financial IQ
            iq_bonus = 2 if passed else 1
            profile.financial_iq_score = min(100, profile.financial_iq_score + iq_bonus)
            profile.save()
            
            return render(request, 'teen/quiz_result.html', {
                'quiz': quiz,
                'score': score,
                'correct_answers': correct_answers,
                'total_questions': total_questions,
                'passed': passed,
                'attempt': attempt,
                'answers_data': answers_data,
                'achievements_unlocked': unlocked.get('unlocked_count', 0) if achievements else 0
            })
        
        # GET request - show quiz
        context = {
            'quiz': quiz,
            'questions': questions,
        }
        
        return render(request, 'teen/quiz_form.html', context)
        
    except Exception as e:
        logger.error(f"Error taking quiz: {e}")
        messages.error(request, "Произошла ошибка при загрузке квиза")
        return redirect('core:learning')


@login_required
def scam_awareness(request):
    """
    Scam awareness and detection module
    """
    try:
        # Get user's scam reports
        scam_reports = ScamAlert.objects.filter(
            user=request.user
        ).order_by('-created_at')[:10]
        
        # Get statistics
        total_reports = scam_reports.count()
        suspicious_reports = scam_reports.filter(is_suspicious=True).count()
        
        context = {
            'scam_reports': scam_reports,
            'total_reports': total_reports,
            'suspicious_reports': suspicious_reports,
        }
        
        return render(request, 'teen/scam_awareness.html', context)
        
    except Exception as e:
        logger.error(f"Error in scam awareness: {e}")
        messages.error(request, "Произошла ошибка при загрузке модуля защиты")
        return redirect('core:dashboard')


@csrf_exempt
@login_required
def report_scam(request):
    """
    Report potential scam for AI analysis
    """
    if request.method == 'POST':
        try:
            user = request.user
            data = json.loads(request.body)
            
            reported_text = data.get('text', '').strip()
            reported_url = data.get('url', '').strip()
            
            if not reported_text and not reported_url:
                return JsonResponse({'error': 'Укажите текст или URL для проверки'}, status=400)
            
            # Analyze with AI
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                analysis = analyze_potential_scam(reported_text, reported_url, user)
            finally:
                loop.close()
            
            # Save scam alert
            scam_alert = ScamAlert.objects.create(
                user=user,
                reported_text=reported_text,
                reported_url=reported_url,
                is_suspicious=analysis['is_suspicious'],
                severity=analysis['severity'],
                risk_score=analysis['risk_score'],
                red_flags=analysis['red_flags'],
                explanation=analysis['explanation'],
                safe_alternatives=analysis['safe_alternatives']
            )
            
            # Update user progress
            progress = user.progress
            progress.scam_reports += 1
            progress.save()
            
            # Check for achievements
            achievements = gamification_engine.check_user_achievements(user)
            if achievements:
                unlocked = gamification_engine.unlock_achievements(user, achievements)
            
            return JsonResponse({
                'alert_id': scam_alert.id,
                'is_suspicious': analysis['is_suspicious'],
                'severity': analysis['severity'],
                'risk_score': analysis['risk_score'],
                'explanation': analysis['explanation'],
                'red_flags': analysis['red_flags'],
                'safe_alternatives': analysis['safe_alternatives'],
                'achievements_unlocked': unlocked.get('unlocked_count', 0) if achievements else 0
            })
            
        except Exception as e:
            logger.error(f"Error reporting scam: {e}")
            return JsonResponse({'error': 'Произошла ошибка при анализе'}, status=500)
    
    return JsonResponse({'error': 'Метод не поддерживается'}, status=405)


async def analyze_potential_scam(text: str, url: str, user) -> Dict[str, Any]:
    """
    Analyze potential scam using AI
    """
    try:
        profile = user.teen_profile
        context = await teen_coach._build_user_context(user)
        
        system_prompt = f"""
Ты - эксперт по кибербезопасности и защите от мошенничества для подростков.
Проанализируй следующий текст или URL на признаки мошенничества.

ПРИЗНАКИ МОШЕННИЧЕСТВА:
- Слишком хорошие предложения (быстрый заработок, бесплатные деньги)
- Давление "ограниченное время"
- Требование личных данных или оплаты вперед
- Необычные способы оплаты (криптовалюта, подарочные карты)
- Поддельные бренды или логотипы
- Орфографические и грамматические ошибки
- Отсутствие контактной информации

Ответь в формате JSON:
{{
    "is_suspicious": true/false,
    "severity": "low/medium/high/critical",
    "risk_score": 0-100,
    "red_flags": ["список красных флагов"],
    "explanation": "подробное объяснение на русском языке",
    "safe_alternatives": ["безопасные альтернативы"]
}}
"""
        
        analysis_text = f"Текст для анализа: {text}\nURL: {url}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": analysis_text}
        ]
        
        response = await llm_manager.chat(messages, temperature=0.3, max_tokens=800)
        
        # Parse JSON response
        try:
            analysis = json.loads(response.content)
        except json.JSONDecodeError:
            # Fallback analysis
            analysis = {
                "is_suspicious": "бесплатн" in text.lower() or "заработок" in text.lower(),
                "severity": "medium",
                "risk_score": 60,
                "red_flags": ["требует анализа специалистом"],
                "explanation": "Потребуется дополнительная проверка этого предложения.",
                "safe_alternatives": ["обратитесь к взрослым за советом"]
            }
        
        return analysis
        
    except Exception as e:
        logger.error(f"Error analyzing potential scam: {e}")
        return {
            "is_suspicious": False,
            "severity": "low",
            "risk_score": 20,
            "red_flags": [],
            "explanation": "Не удалось провести анализ. Будьте осторожны с незнакомыми предложениями.",
            "safe_alternatives": ["не переходите по подозрительным ссылкам"]
        }


@login_required
def achievements_view(request):
    """
    User achievements and progress tracking
    """
    try:
        user = request.user
        
        # Get user achievements
        user_achievements = UserAchievement.objects.filter(
            user=user
        ).select_related('achievement').order_by('-earned_at')
        
        # Get all available achievements
        all_achievements = Achievement.objects.filter(is_active=True)
        
        # Categorize achievements
        earned_achievement_ids = set(user_achievements.values_list('achievement_id', flat=True))
        
        earned_achievements = []
        available_achievements = []
        
        for achievement in all_achievements:
            if achievement.id in earned_achievement_ids:
                earned_achievements.append(achievement)
            else:
                # Calculate progress
                check_result = gamification_engine._check_single_achievement(user, achievement)
                progress_percent = gamification_engine._calculate_achievement_progress(
                    check_result.progress, achievement.criteria
                )
                available_achievements.append({
                    'achievement': achievement,
                    'progress': progress_percent
                })
        
        # Get gamification data
        gamification_data = gamification_engine.get_user_dashboard_data(user)
        
        context = {
            'earned_achievements': earned_achievements,
            'available_achievements': available_achievements,
            'user_achievements': user_achievements,
            'gamification': gamification_data,
        }
        
        return render(request, 'teen/achievements.html', context)
        
    except Exception as e:
        logger.error(f"Error in achievements view: {e}")
        messages.error(request, "Произошла ошибка при загрузке достижений")
        return redirect('core:dashboard')


def get_demo_data():
    """
    Get demo data for hackathon presentation
    """
    return {
        'demo_user': {
            'name': 'Айжан',
            'age': 16,
            'monthly_allowance': 5000,
            'currency': 'KGS'
        },
        'demo_goals': [
            {
                'title': 'iPhone 15',
                'target_amount': 80000,
                'current_amount': 25000,
                'progress': 31,
                'target_date': '2025-06-01'
            },
            {
                'title': 'Курсы программирования',
                'target_amount': 15000,
                'current_amount': 8000,
                'progress': 53,
                'target_date': '2025-04-15'
            }
        ],
        'demo_achievements': [
            {'title': 'Первые шаги', 'icon': '🚀', 'category': 'milestone'},
            {'title': 'Накопитель', 'icon': '💰', 'category': 'saving'},
            {'title': 'Ученик', 'icon': '📚', 'category': 'learning'}
        ],
        'demo_insights': [
            {
                'title': 'Совет недели',
                'content': 'Ты тратишь 40% денег на развлечения. Попробуй снизить до 30%!'
            }
        ]
    }


@login_required
def toggle_demo_mode(request):
    """
    Toggle demo mode for presentations
    """
    if request.method == 'POST':
        try:
            profile = request.user.teen_profile
            profile.demo_mode = not profile.demo_mode
            profile.save()
            
            status = "включен" if profile.demo_mode else "выключен"
            messages.success(request, f"Демо-режим {status}")
            
        except Exception as e:
            logger.error(f"Error toggling demo mode: {e}")
            messages.error(request, "Произошла ошибка при изменении режима")
    
    return redirect('teen:dashboard')