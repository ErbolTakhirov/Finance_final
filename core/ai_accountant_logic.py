import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from django.db.models import Sum, Avg
from .models import Income, Expense, Transaction, MonthlySummary, UserGoal, AIRecommendationLog
from .llm import chat_with_context

def sync_transactions_from_legacy(user):
    """Sync Income and Expense models to unified Transaction model"""
    # Sync Incomes
    incomes = Income.objects.filter(user=user)
    for inc in incomes:
        Transaction.objects.update_or_create(
            user=user,
            legacy_id=inc.id,
            legacy_type='income',
            defaults={
                'date': inc.date,
                'amount': inc.amount,
                'type': 'income',
                'category': inc.get_income_type_display(),
                'description': inc.description or "",
                'source': inc.source or 'legacy'
            }
        )
    
    # Sync Expenses
    expenses = Expense.objects.filter(user=user)
    for exp in expenses:
        Transaction.objects.update_or_create(
            user=user,
            legacy_id=exp.id,
            legacy_type='expense',
            defaults={
                'date': exp.date,
                'amount': -exp.amount,
                'type': 'expense',
                'category': exp.get_expense_type_display(),
                'description': exp.description or "",
                'source': 'legacy'
            }
        )

def calculate_monthly_summaries(user):
    """Calculate and store MonthlySummary from Transaction model"""
    transactions = Transaction.objects.filter(user=user)
    if not transactions.exists():
        return
    
    data = []
    for tx in transactions:
        data.append({
            'month_key': tx.month_key,
            'amount': float(tx.amount),
            'type': tx.type
        })
    
    df = pd.DataFrame(data)
    
    summary = df.groupby('month_key').apply(lambda x: pd.Series({
        'total_income': x[x['type'] == 'income']['amount'].sum(),
        'total_expense': -x[x['type'] == 'expense']['amount'].sum(),
    })).reset_index()
    
    summary['profit'] = summary['total_income'] - summary['total_expense']
    
    for _, row in summary.iterrows():
        MonthlySummary.objects.update_or_create(
            user=user,
            month_key=row['month_key'],
            defaults={
                'total_income': row['total_income'],
                'total_expense': row['total_expense'],
                'profit': row['profit']
            }
        )

def get_profit_forecast(user):
    """
    Predict next month profit and provide AI explanation.
    """
    summaries = MonthlySummary.objects.filter(user=user).order_by('month_key')
    if summaries.count() < 3:
        # Qualitative advice only
        prompt = "Данных о прибыли за последние 3 месяца недостаточно. Дай общие советы по увеличению прибыли и экономии для пользователя FinTech приложения."
        advice = chat_with_context([], user_data=prompt, user=user)
        return None, advice
    
    profits = [float(s.profit) for s in summaries]
    x = np.arange(len(profits))
    y = np.array(profits)
    z = np.polyfit(x, y, 1)
    p = np.poly1d(z)
    
    forecasted_profit = p(len(profits))
    
    # AI Explanation
    history_str = "\n".join([f"{s.month_key}: Прибыль {s.profit}" for s in summaries])
    prompt = f"""
Проанализируй историю прибыли пользователя и объясни прогноз на следующий месяц.
История:
{history_str}

Прогноз на следующий месяц: {forecasted_profit:.2f}

Объясни тренд (растет/падает), выдели возможные причины и дай 2-3 конкретных совета, как улучшить результат.
Пиши просто и понятно, как AI-бухгалтер.
"""
    explanation = chat_with_context([], user_data=prompt, user=user)
    
    # Log recommendation
    AIRecommendationLog.objects.create(
        user=user,
        text=explanation,
        recommendation_type='forecast_advice',
        month_key=datetime.now().strftime('%Y-%m')
    )
    
    return forecasted_profit, explanation

def update_goal_coaching(user, goal):
    """Update goal progress predictions and get AI advice"""
    summaries = MonthlySummary.objects.filter(user=user).order_by('-month_key')[:3]
    if not summaries.exists():
        return "Недостаточно данных для анализа прогресса по цели.", 0
        
    avg_profit = float(summaries.aggregate(Avg('profit'))['profit__avg'] or 0)
    
    remaining_amount = float(goal.target_amount - goal.current_amount)
    
    if avg_profit <= 0:
        months_needed = 999
        probability = 5
    else:
        months_needed = remaining_amount / avg_profit
        
        days_left = (goal.target_date - date.today()).days
        months_left = days_left / 30.0
        
        if months_left <= 0:
            probability = 0
        elif months_needed <= months_left:
            # On track
            probability = min(99, 70 + int((months_left - months_needed) * 10))
        else:
            # Behind schedule
            probability = max(5, 50 - int((months_needed - months_left) * 10))

    if avg_profit > 0:
        projected_date = date.today() + timedelta(days=int(months_needed * 30))
    else:
        projected_date = None

    # Update goal
    goal.projected_date_if_current_trend = projected_date
    goal.probability_of_success = probability
    
    history_str = "\n".join([f"{s.month_key}: {s.profit}" for s in summaries])
    prompt = f"""
Ты AI-коуч по финансовым целям.
Цель: {goal.title}
Нужно накопить еще: {remaining_amount} {user.teen_profile.currency if hasattr(user, 'teen_profile') else 'KGS'}
Дедлайн: {goal.target_date}

Твоя статистика прибыли за последние месяцы:
{history_str}
Средняя прибыль: {avg_profit:.2f}

Оцени вероятность успеха ({probability}%) и дай конкретные советы.
Если вероятность низкая, предложи урезать расходы в категориях (предположи каких) или найти подработку.
"""
    advice = chat_with_context([], user_data=prompt, user=user)
    goal.ai_recommendation = advice
    goal.save()
    
    AIRecommendationLog.objects.create(
        user=user,
        goal=goal,
        text=advice,
        recommendation_type='goal_progress'
    )
    
    return advice, probability

def get_monthly_report(user, month_key=None):
    """AI Accountant monthly report"""
    if not month_key:
        month_key = (date.today().replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
    
    summary = MonthlySummary.objects.filter(user=user, month_key=month_key).first()
    if not summary:
        return f"Нет данных за {month_key}."
    
    transactions = Transaction.objects.filter(user=user, month_key=month_key)
    # Get top expense categories
    expenses = transactions.filter(type='expense')
    cat_summary = expenses.values('category').annotate(total=Sum('amount')).order_by('total') # amount is negative
    
    cat_str = "\n".join([f"- {c['category']}: {-c['total']:.2f}" for c in cat_summary[:5]])
    
    prompt = f"""
Отчет AI-бухгалтера за {month_key}.
Доходы: {summary.total_income}
Расходы: {summary.total_expense}
Прибыль: {summary.profit}

Топ категорий расходов:
{cat_str}

Проанализируй эти данные. Объясни, на что ушло больше всего денег и как это повлияло на прибыль. 
Дай совет на следующий месяц.
"""
    report = chat_with_context([], user_data=prompt, user=user)
    
    AIRecommendationLog.objects.create(
        user=user,
        month_key=month_key,
        text=report,
        recommendation_type='general_advice'
    )
    
    return report
