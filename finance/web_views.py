import json

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone

from finance.forms import TransactionForm
from finance.models import Transaction, MonthlySummary
from finance.services.accounting import AccountingService
from goals.models import Goal


@login_required
def dashboard(request):
    user = request.user

    month_key = timezone.now().date().strftime('%Y-%m')
    current_summary = MonthlySummary.objects.filter(user=user, month_key=month_key).first()

    active_goals = Goal.objects.filter(user=user, status='active').order_by('target_date')
    months = AccountingService.get_months(user=user)

    summaries = MonthlySummary.objects.filter(user=user).order_by('month_key')
    history_data = [
        {'month': s.month_key, 'profit': float(s.profit)}
        for s in summaries
    ]

    context = {
        'current_summary': current_summary,
        'active_goals': active_goals,
        'months': months,
        'default_month_key': month_key,
        'history_json': json.dumps(history_data),
    }
    return render(request, 'dashboard.html', context)


@login_required
def transactions_page(request):
    user = request.user

    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            AccountingService.create_transaction(user=user, **form.cleaned_data)
            return redirect('transactions')
    else:
        form = TransactionForm()

    transactions = Transaction.objects.filter(user=user).order_by('-date', '-created_at')[:200]
    summaries = MonthlySummary.objects.filter(user=user).order_by('-month_key')[:12]

    context = {
        'form': form,
        'transactions': transactions,
        'summaries': summaries,
    }
    return render(request, 'transactions.html', context)
