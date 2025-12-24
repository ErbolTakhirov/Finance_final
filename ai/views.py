from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from finance.models import MonthlySummary
from finance.services.accounting import AccountingService
from finance.services.forecast import ForecastService
from goals.models import Goal
from ai.services import AIService, AIServiceError


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def monthly_report(request):
    user = request.user
    month_key = request.data.get('month_key')
    if not month_key:
        from django.utils import timezone

        month_key = timezone.now().date().strftime('%Y-%m')

    summary = MonthlySummary.objects.filter(user=user, month_key=month_key).first()
    if not summary:
        return Response({'error': f'No data for month {month_key}'}, status=status.HTTP_404_NOT_FOUND)

    top_categories = AccountingService.top_expense_categories(user=user, month_key=month_key, limit=5)

    ai_service = AIService()
    try:
        report = ai_service.generate_monthly_report(
            user=user,
            month_key=month_key,
            summary=summary,
            top_categories=top_categories,
        )
        return Response({'report': report}, status=status.HTTP_200_OK)
    except AIServiceError as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def goal_advice(request):
    user = request.user
    goal_id = request.data.get('goal_id')

    if not goal_id:
        return Response({'error': 'goal_id required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        goal = Goal.objects.get(id=goal_id, user=user)
    except Goal.DoesNotExist:
        return Response({'error': 'Goal not found'}, status=status.HTTP_404_NOT_FOUND)

    summaries = MonthlySummary.objects.filter(user=user).order_by('month_key')
    history = [
        {'month_key': s.month_key, 'profit': str(s.profit)}
        for s in summaries
    ]

    forecast_result = ForecastService.forecast_next_month(list(summaries))
    forecast_data = ForecastService.as_dict(forecast_result) if forecast_result.status == 'ok' else None

    ai_service = AIService()
    try:
        advice = ai_service.generate_goal_progress_advice(
            user=user,
            goal=goal,
            history=history,
            forecast=forecast_data,
        )
        return Response({'advice': advice}, status=status.HTTP_200_OK)
    except AIServiceError as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def forecast_view(request):
    user = request.user

    summaries = MonthlySummary.objects.filter(user=user).order_by('month_key')

    result = ForecastService.forecast_next_month(list(summaries))

    if result.status == 'insufficient_data':
        return Response({
            'status': 'insufficient_data',
            'message': 'Требуется минимум 3 месяца данных для прогноза',
        }, status=status.HTTP_200_OK)

    ai_service = AIService()
    try:
        explanation = ai_service.generate_forecast_explanation(
            user=user,
            forecast=ForecastService.as_dict(result),
            history=list(summaries),
        )
        return Response({
            'status': 'ok',
            'predicted_profit': str(result.predicted_profit),
            'lower': str(result.lower),
            'upper': str(result.upper),
            'algorithm': result.algorithm,
            'used_months': result.used_months,
            'explanation': explanation,
        }, status=status.HTTP_200_OK)
    except AIServiceError as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
