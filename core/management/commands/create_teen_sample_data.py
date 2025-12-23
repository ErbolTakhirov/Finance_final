"""
Sample data for FinBilim 2025 Teen FinTech MVP
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from core.models import (
    Achievement, LearningModule, Quiz, QuizQuestion, UserProfile, UserProgress
)
from datetime import datetime, timedelta
import random


class Command(BaseCommand):
    help = 'Create sample data for Teen FinTech MVP'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write('Creating sample data for FinBilim 2025...')
        
        # Create achievements
        self.create_achievements()
        
        # Create learning modules
        self.create_learning_modules()
        
        # Create demo user
        self.create_demo_user()
        
        self.stdout.write(
            self.style.SUCCESS('Sample data created successfully!')
        )

    def create_achievements(self):
        """Create achievement templates"""
        achievements_data = [
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
                'title': 'Накопитель',
                'description': 'Накопил 50% от цели',
                'category': 'saving',
                'icon': '💰',
                'criteria': {'type': 'goal_progress', 'value': 50},
                'points': 30,
                'iq_bonus': 3
            },
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
                'title': 'Защитник',
                'description': 'Использовал модуль защиты от мошенничества',
                'category': 'security',
                'icon': '🛡️',
                'criteria': {'type': 'scam_checks', 'value': 1},
                'points': 30,
                'iq_bonus': 3
            },
            {
                'title': 'Постоянство',
                'description': 'Заходил в приложение 7 дней подряд',
                'category': 'streak',
                'icon': '🔥',
                'criteria': {'type': 'login_streak', 'value': 7},
                'points': 25,
                'iq_bonus': 3
            }
        ]
        
        for achievement_data in achievements_data:
            achievement, created = Achievement.objects.get_or_create(
                title=achievement_data['title'],
                defaults=achievement_data
            )
            if created:
                self.stdout.write(f'Created achievement: {achievement.title}')

    def create_learning_modules(self):
        """Create sample learning modules with quizzes"""
        modules_data = [
            {
                'title': 'Основы бюджетирования',
                'slug': 'budgeting-basics',
                'description': 'Изучите, как составить и вести личный бюджет',
                'content': '''
                    <h3>Что такое бюджет?</h3>
                    <p>Бюджет - это план того, как вы будете тратить и откладывать свои деньги. Это поможет вам контролировать расходы и достигать целей.</p>
                    
                    <h3>Как составить бюджет:</h3>
                    <ol>
                        <li><strong>Подсчитайте доходы</strong> - сколько денег вы получаете в месяц</li>
                        <li><strong>Запишите все расходы</strong> - еда, транспорт, развлечения, покупки</li>
                        <li><strong>Определите цели</strong> - на что хотите накопить</li>
                        <li><strong>Распределите деньги</strong> - сколько на что потратить</li>
                    </ol>
                    
                    <h3>Правило 50/30/20</h3>
                    <p>Отличное правило для подростков:</p>
                    <ul>
                        <li>50% - обязательные расходы (еда, транспорт)</li>
                        <li>30% - развлечения и покупки</li>
                        <li>20% - накопления и цели</li>
                    </ul>
                ''',
                'difficulty': 'beginner',
                'estimated_time': 15,
                'category': 'budgeting',
                'learning_objectives': [
                    'Понять, что такое бюджет',
                    'Научиться составлять простой бюджет',
                    'Узнать правило 50/30/20'
                ],
                'is_published': True
            },
            {
                'title': 'Защита от мошенничества',
                'slug': 'scam-protection',
                'description': 'Узнайте, как распознать мошенников и защитить свои деньги',
                'content': '''
                    <h3>Основные признаки мошенничества:</h3>
                    <ul>
                        <li><strong>Слишком хорошие предложения</strong> - быстрый заработок, бесплатные призы</li>
                        <li><strong>Давление</strong> - "действуйте прямо сейчас", "только сегодня"</li>
                        <li><strong>Просьба перевести деньги</strong> или дать банковские данные</li>
                        <li><strong>Необычные способы оплаты</strong> - криптовалюта, подарочные карты</li>
                    </ul>
                    
                    <h3>Как защититься:</h3>
                    <ol>
                        <li>Никогда не переводите деньги незнакомцам</li>
                        <li>Проверяйте информацию на официальных сайтах</li>
                        <li>Советуйтесь с родителями или взрослыми</li>
                        <li>Используйте наше приложение для проверки подозрительных предложений</li>
                    </ol>
                ''',
                'difficulty': 'beginner',
                'estimated_time': 10,
                'category': 'security',
                'learning_objectives': [
                    'Распознавать основные признаки мошенничества',
                    'Знать способы защиты от мошенников',
                    'Понимать, когда обращаться за помощью'
                ],
                'is_published': True
            },
            {
                'title': 'Искусство накоплений',
                'slug': 'saving-basics',
                'description': 'Научитесь эффективно копить деньги на свои цели',
                'content': '''
                    <h3>Почему важно копить?</h3>
                    <p>Накопления помогают:</p>
                    <ul>
                        <li>Достигать больших целей (телефон, ноутбук, поездка)</li>
                        <li>Быть готовыми к неожиданным расходам</li>
                        <li>Чувствовать себя уверенно с финансами</li>
                    </ul>
                    
                    <h3>Лайфхаки для экономии:</h3>
                    <ol>
                        <li><strong>Правило сдачи</strong> - откладывайте всю сдачу от покупок</li>
                        <li><strong>Недельные лимиты</strong> - определите, сколько можете потратить</li>
                        <li><strong>Ждите 24 часа</strong> - перед спонтанной покупкой подумайте сутки</li>
                        <li><strong>Открывайте цель в приложении</strong> - видеть прогресс мотивирует</li>
                    </ol>
                    
                    <h3>Пример накоплений:</h3>
                    <p>Если копить 500 сом в месяц на iPhone за 80,000 сом, то понадобится 160 месяцев (13 лет)! Поэтому лучше:</p>
                    <ul>
                        <li>Найти подработку</li>
                        <li>Копить больше с каждой стипендии</li>
                        <li>Рассмотреть более доступную цель</li>
                    </ul>
                ''',
                'difficulty': 'beginner',
                'estimated_time': 12,
                'category': 'saving',
                'learning_objectives': [
                    'Понимать важность накоплений',
                    'Изучить практические способы экономии',
                    'Уметь рассчитать время достижения целей'
                ],
                'is_published': True
            }
        ]
        
        for module_data in modules_data:
            module, created = LearningModule.objects.get_or_create(
                slug=module_data['slug'],
                defaults=module_data
            )
            
            if created:
                self.stdout.write(f'Created learning module: {module.title}')
                
                # Create quiz for this module
                quiz = Quiz.objects.create(
                    module=module,
                    title=f'Квиз: {module.title}',
                    description=f'Проверьте свои знания по теме "{module.title}"',
                    questions_count=3,
                    passing_score=70
                )
                
                # Create sample questions
                if module.slug == 'budgeting-basics':
                    questions = [
                        {
                            'question_text': 'Что такое бюджет?',
                            'option_a': 'План трат денег на определенный период',
                            'option_b': 'Количество денег в кошельке',
                            'option_c': 'Банковский счет',
                            'option_d': 'Кредитная карта',
                            'correct_answer': 'A',
                            'explanation': 'Бюджет - это план того, как вы будете распоряжаться деньгами.'
                        },
                        {
                            'question_text': 'По правилу 50/30/20 сколько процентов дохода нужно откладывать?',
                            'option_a': '10%',
                            'option_b': '20%',
                            'option_c': '30%',
                            'option_d': '50%',
                            'correct_answer': 'B',
                            'explanation': 'По правилу 50/30/20 нужно откладывать 20% дохода.'
                        },
                        {
                            'question_text': 'Обязательные расходы - это...',
                            'option_a': 'Покупка новой одежды',
                            'option_b': 'Еда и транспорт',
                            'option_c': 'Игры и развлечения',
                            'option_d': 'Фотографии для соцсетей',
                            'correct_answer': 'B',
                            'explanation': 'Обязательные расходы - это то, без чего нельзя обойтись.'
                        }
                    ]
                elif module.slug == 'scam-protection':
                    questions = [
                        {
                            'question_text': 'Какой признак указывает на мошенничество?',
                            'option_a': 'Предложение быстро заработать много денег',
                            'option_b': 'Обычное предложение работы',
                            'option_c': 'Реклама магазина',
                            'option_d': 'Сообщение от друга',
                            'correct_answer': 'A',
                            'explanation': 'Слишком хорошие предложения - классический признак мошенничества.'
                        },
                        {
                            'question_text': 'Что нужно делать при подозрительном предложении?',
                            'option_a': 'Сразу согласиться',
                            'option_b': 'Посоветоваться со взрослыми',
                            'option_c': 'Перевести деньги для проверки',
                            'option_d': 'Игнорировать все предложения',
                            'correct_answer': 'B',
                            'explanation': 'При сомнениях всегда советуйтесь с родителями или другими взрослыми.'
                        }
                    ]
                elif module.slug == 'saving-basics':
                    questions = [
                        {
                            'question_text': 'Что такое "правило сдачи"?',
                            'option_a': 'Копить только крупные купюры',
                            'option_b': 'Откладывать всю сдачу от покупок',
                            'option_c': 'Не тратить мелочь',
                            'option_d': 'Носить сдачу в банк',
                            'correct_answer': 'B',
                            'explanation': 'Правило сдачи - это простой способ начать копить, откладывая мелочь.'
                        },
                        {
                            'question_text': 'Сколько времени понадобится на накопление 80,000 сом, если копить по 500 сом в месяц?',
                            'option_a': '16 месяцев',
                            'option_b': '160 месяцев',
                            'option_c': '80 месяцев',
                            'option_d': '8 месяцев',
                            'correct_answer': 'B',
                            'explanation': '80,000 ÷ 500 = 160 месяцев (около 13 лет)'
                        }
                    ]
                
                for i, q_data in enumerate(questions):
                    QuizQuestion.objects.create(
                        quiz=quiz,
                        question_text=q_data['question_text'],
                        option_a=q_data['option_a'],
                        option_b=q_data['option_b'],
                        option_c=q_data.get('option_c', ''),
                        option_d=q_data.get('option_d', ''),
                        correct_answer=q_data['correct_answer'],
                        explanation=q_data['explanation'],
                        order=i
                    )

    def create_demo_user(self):
        """Create demo user for presentations"""
        demo_user, created = User.objects.get_or_create(
            username='demo_teen',
            defaults={
                'email': 'demo@sb-finance.ai',
                'first_name': 'Айжан',
                'last_name': 'Демо'
            }
        )
        
        if created:
            demo_user.set_password('demo123')
            demo_user.save()
            self.stdout.write('Created demo user: demo_teen (password: demo123)')
            
            # Create profile
            profile = UserProfile.objects.create(
                user=demo_user,
                age=16,
                monthly_allowance=5000,
                preferred_language='ru',
                financial_iq_score=25,
                current_streak=3,
                longest_streak=7,
                demo_mode=True
            )
            
            # Create progress
            UserProgress.objects.create(
                user=demo_user,
                goals_created=2,
                goals_achieved=1,
                ai_conversations=5,
                last_activity=datetime.now()
            )
            
            # Create sample goals
            from core.models import UserGoal
            from datetime import datetime, timedelta
            
            goal1 = UserGoal.objects.create(
                user=demo_user,
                title='iPhone 15',
                description='Новый iPhone 15 128GB',
                target_amount=80000,
                current_amount=25000,
                category='electronics',
                target_date=datetime.now() + timedelta(days=180),
                ai_recommendation='Попробуйте увеличить подработку или уменьшить траты на развлечения на 20%. Можете также откладывать все деньги от подарков на день рождения.',
                weekly_saving_suggestion=1000
            )
            
            goal2 = UserGoal.objects.create(
                user=demo_user,
                title='Курсы программирования',
                description='Курс по Python в IT Academy Bishkek',
                target_amount=15000,
                current_amount=8000,
                category='education',
                target_date=datetime.now() + timedelta(days=90),
                ai_recommendation='Отличная цель! Продолжайте в том же духе. Можно поискать скидки на курсы или попросить родителей оплатить часть.',
                weekly_saving_suggestion=800
            )