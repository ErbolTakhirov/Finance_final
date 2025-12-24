from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Transaction, MonthlySummary, UserGoal, AIRecommendationLog, Income, Expense
from .ai_accountant_logic import (
    sync_transactions_from_legacy,
    calculate_monthly_summaries,
    get_profit_forecast,
    update_goal_coaching,
    get_monthly_report
)
from datetime import date, datetime, timedelta
import json
import random

@login_required
def setup_ai_accountant_demo(request):
    user = request.user
    
    # Generate 6 months of history
    today = date.today()
    for i in range(6, -1, -1):
        # Calculate year and month
        month = today.month - i
        year = today.year
        while month <= 0:
            month += 12
            year -= 1
        
        month_date = date(year, month, 1)
        month_key = month_date.strftime('%Y-%m')
        
        # Monthly income
        base_income = 50000 + random.randint(-5000, 10000)
        Transaction.objects.get_or_create(
            user=user,
            date=month_date.replace(day=5),
            type='income',
            defaults={
                'amount': base_income,
                'category': 'Зарплата',
                'description': 'Основной доход',
                'month_key': month_key
            }
        )
        
        # Monthly expenses
        expenses = [
            ('Аренда', 15000, 1),
            ('Еда', 12000 + random.randint(-2000, 4000), 15),
            ('Транспорт', 3000 + random.randint(0, 2000), 20),
            ('Развлечения', 5000 + random.randint(-1000, 10000), 25),
        ]
        
        for cat, amt, day in expenses:
            Transaction.objects.get_or_create(
                user=user,
                date=month_date.replace(day=day),
                type='expense',
                category=cat,
                defaults={
                    'amount': -amt,
                    'month_key': month_key
                }
            )
        
    # Create a goal if none exists
    if not UserGoal.objects.filter(user=user).exists():
        UserGoal.objects.create(
            user=user,
            title='На новый MacBook',
            target_amount=180000,
            current_amount=45000,
            category='electronics',
            target_date=today + timedelta(days=365),
            status='active'
        )
    
    # Recalculate summaries
    calculate_monthly_summaries(user)
    
    messages.success(request, "Демо-данные успешно созданы! Теперь вы можете увидеть прогнозы и аналитику.")
    return redirect('ai_accountant_dashboard')

@login_required
def ai_accountant_dashboard(request):
    user = request.user
    # Ensure data is synced for the demo
    sync_transactions_from_legacy(user)
    calculate_monthly_summaries(user)
    
    today = date.today()
    month_key = today.strftime('%Y-%m')
    
    current_summary = MonthlySummary.objects.filter(user=user, month_key=month_key).first()
    active_goals = UserGoal.objects.filter(user=user, status='active')
    
    latest_recommendations = AIRecommendationLog.objects.filter(user=user).order_by('-created_at')[:3]
    
    context = {
        'current_summary': current_summary,
        'active_goals': active_goals,
        'latest_recommendations': latest_recommendations,
        'month_key': month_key,
    }
    return render(request, 'ai_accountant/dashboard.html', context)

@login_required
def ai_transactions_view(request):
    user = request.user
    transactions = Transaction.objects.filter(user=user).order_by('-date')
    summaries = MonthlySummary.objects.filter(user=user).order_by('-month_key')
    
    context = {
        'transactions': transactions,
        'summaries': summaries,
    }
    return render(request, 'ai_accountant/transactions.html', context)

@login_required
def ai_goal_detail(request, goal_id):
    user = request.user
    goal = get_object_or_404(UserGoal, id=goal_id, user=user)
    
    # Get or update AI advice
    advice, probability = update_goal_coaching(user, goal)
    
    forecast_profit, forecast_explanation = get_profit_forecast(user)
    
    summaries = MonthlySummary.objects.filter(user=user).order_by('month_key')
    history_data = [
        {'month': s.month_key, 'profit': float(s.profit)} for s in summaries
    ]
    
    context = {
        'goal': goal,
        'advice': advice,
        'probability': probability,
        'forecast_profit': forecast_profit,
        'forecast_explanation': forecast_explanation,
        'history_data_json': json.dumps(history_data),
    }
    return render(request, 'ai_accountant/goal_detail.html', context)

@login_required
def ai_monthly_report_api(request):
    user = request.user
    month_key = request.GET.get('month_key')
    report = get_monthly_report(user, month_key)
    return JsonResponse({'report': report})

@login_required
def ai_forecast_whatif(request):
    user = request.user
    goal_id = request.GET.get('goal_id')
    income_change = float(request.GET.get('income_change', 0))
    expense_change = float(request.GET.get('expense_change', 0))
    
    summaries = MonthlySummary.objects.filter(user=user).order_by('-month_key')[:3]
    if not summaries.exists():
        return JsonResponse({'error': 'Недостаточно данных'})
        
    import django.db.models as db_models
    avg_income = float(summaries.aggregate(db_models.Avg('total_income'))['total_income__avg'] or 0)
    avg_expense = float(summaries.aggregate(db_models.Avg('total_expense'))['total_expense__avg'] or 0)
    
    new_income = avg_income + income_change
    new_expense = avg_expense - expense_change # expense_change is positive amount to cut
    new_profit = new_income - new_expense
    
    result = {
        'new_profit': new_profit,
    }
    
    if goal_id:
        goal = UserGoal.objects.get(id=goal_id)
        remaining = float(goal.target_amount - goal.current_amount)
        if new_profit <= 0:
            new_months = 999
            new_date = "Никогда"
        else:
            new_months = remaining / new_profit
            from datetime import timedelta
            new_date = (date.today() + timedelta(days=int(new_months * 30))).strftime('%Y-%m-%d')
        result['new_date'] = new_date
        
    return JsonResponse(result)

@login_required
def ai_forecast_page(request):
    user = request.user
    goals = UserGoal.objects.filter(user=user, status='active')
    forecast_profit, forecast_explanation = get_profit_forecast(user)
    
    summaries = MonthlySummary.objects.filter(user=user).order_by('month_key')
    history_data = [
        {'month': s.month_key, 'profit': float(s.profit)} for s in summaries
    ]
    
    context = {
        'goals': goals,
        'forecast_profit': forecast_profit,
        'forecast_explanation': forecast_explanation,
        'history_data_json': json.dumps(history_data),
    }
    return render(request, 'ai_accountant/forecast.html', context)
