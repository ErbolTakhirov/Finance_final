import json
import asyncio
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from core.models import Income, Expense, UserGoal, FinancialInsight
from core.services.finance_automation import finance_automation

@login_required
def import_data_view(request):
    """
    Page where users can paste raw financial text or upload files.
    """
    if request.method == 'POST':
        raw_text = request.POST.get('raw_data', '')
        if not raw_text:
            messages.warning(request, "Пожалуйста, введите данные.")
            return redirect('core:import_data')
        
        # 1. Parse text
        parsed_data = finance_automation.parse_raw_text(raw_text)
        
        # 2. Categorize with AI (simplified async call)
        # In a real heavy app, this would be a Celery task.
        # For a hackathon, we do it inline for UX.
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            categorized_data = loop.run_until_complete(
                finance_automation.categorize_with_ai(parsed_data, request.user)
            )
        finally:
            loop.close()
        
        # Store in session for review
        request.session['pending_transactions'] = categorized_data
        return redirect('core:review_data')

    return render(request, 'teen/import.html')

@login_required
def review_transactions_view(request):
    """
    Step 2: User reviews AI-categorized transactions and saves them.
    Allows linking income to goals.
    """
    pending = request.session.get('pending_transactions', [])
    goals = request.user.goals.filter(status='active')
    
    if not pending:
        messages.info(request, "Нет транзакций для обработки.")
        return redirect('core:import_data')

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'confirm_all':
            for i, item in enumerate(pending):
                # Check if goal was selected for this transaction
                goal_id = request.POST.get(f'goal_{i}')
                
                if item['type'] == 'expense':
                    obj = Expense.objects.create(
                        user=request.user,
                        amount=item['amount'],
                        date=item['date'],
                        expense_type=item['category'],
                        merchant=item['merchant'],
                        description=item['description'],
                        needs_review=False
                    )
                else:
                    obj = Income.objects.create(
                        user=request.user,
                        amount=item['amount'],
                        date=item['date'],
                        income_type=item['category'],
                        merchant=item['merchant'],
                        description=item['description'],
                        needs_review=False
                    )
                    # If goal selected, update its progress
                    if goal_id:
                        finance_automation.link_transaction_to_goal(request.user, obj, goal_id)
            
            del request.session['pending_transactions']
            messages.success(request, f"Успешно обработано {len(pending)} транзакций!")
            return redirect('core:dashboard')

    return render(request, 'teen/review.html', {
        'transactions': pending,
        'goals': goals
    })

@login_required
def ai_insights_view(request):
    """
    Advanced AI insights, money leaks, and forecasts.
    """
    leaks = finance_automation.get_money_leaks(request.user)
    forecast = finance_automation.get_forecast(request.user)
    
    # Generate real AI advice
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        ai_advice = loop.run_until_complete(
            finance_automation.generate_ai_advice(request.user)
        )
    finally:
        loop.close()

    context = {
        'leaks': leaks,
        'forecast': forecast,
        'ai_advice': ai_advice,
    }
    return render(request, 'teen/insights.html', context)
