import json

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from finance.models import MonthlySummary
from finance.services.forecast import ForecastService
from goals.models import Goal
from goals.forms import GoalForm
from goals.services import GoalService


@login_required
def goals_page(request):
    user = request.user

    if request.method == 'POST':
        form = GoalForm(request.POST)
        if form.is_valid():
            GoalService.create_goal(user=user, **form.cleaned_data)
            return redirect('goals_page')
    else:
        form = GoalForm()

    all_goals = Goal.objects.filter(user=user).order_by('-status', 'target_date')

    context = {
        'form': form,
        'goals': all_goals,
    }
    return render(request, 'goals_list.html', context)


@login_required
def goal_detail_page(request, goal_id):
    user = request.user
    goal = get_object_or_404(Goal, id=goal_id, user=user)

    progress = GoalService.calculate_progress(goal)

    summaries = MonthlySummary.objects.filter(user=user).order_by('month_key')
    history_data = [
        {'month': s.month_key, 'profit': float(s.profit)} for s in summaries
    ]

    forecast_result = ForecastService.forecast_next_month(list(summaries))

    context = {
        'goal': goal,
        'progress': progress,
        'history_json': json.dumps(history_data),
        'forecast': forecast_result,
    }
    return render(request, 'goal_detail.html', context)
