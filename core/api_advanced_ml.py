"""
Advanced ML API Views
Provides endpoints for advanced ML features:
- Advanced forecasting (Prophet, ARIMA, LSTM)
- Anomaly detection (Isolation Forest, etc.)
- Clustering and segmentation
- Model explainability (SHAP)
- Advanced analytics (Monte Carlo, time series decomposition)
- Interactive visualizations
"""

import json
from datetime import date
from typing import Dict, Any

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render

from .models import Income, Expense
from .ml.advanced_forecasting import AdvancedForecaster
from .ml.advanced_classifier import AdvancedExpenseClassifier
from .ml.anomaly_detection import AdvancedAnomalyDetector
from .ml.clustering import TransactionClusterer
from .ml.explainability import create_explainer_for_model
from .ml.advanced_analytics import (
    MonteCarloSimulator,
    TimeSeriesAnalyzer,
    CohortAnalyzer,
    StatisticalTester
)
from .ml.visualization import AdvancedVisualizer


@login_required
def ml_showcase_view(request):
    """Render ML showcase page"""
    return render(request, 'ml_showcase.html')


@login_required
@require_http_methods(['POST'])
def advanced_forecast_api(request):
    """
    Advanced forecasting using Prophet, ARIMA, LSTM, or ensemble
    
    POST params:
        - method: 'auto', 'prophet', 'arima', 'lstm', 'ensemble'
        - periods: number of days to forecast (default: 30)
        - monthly: if true, return monthly aggregated forecast
    """
    try:
        data = json.loads(request.body)
        method = data.get('method', 'auto')
        periods = int(data.get('periods', 30))
        monthly = data.get('monthly', False)
        
        incomes = Income.objects.filter(user=request.user)
        expenses = Expense.objects.filter(user=request.user)
        
        forecaster = AdvancedForecaster(method=method)
        
        if monthly:
            months = int(data.get('months', 6))
            result = forecaster.get_monthly_forecast(incomes, expenses, months=months)
        else:
            result = forecaster.forecast(incomes, expenses, periods=periods)
        
        return JsonResponse(result)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(['POST'])
def anomaly_detection_api(request):
    """
    Advanced anomaly detection using multiple algorithms
    
    POST params:
        - contamination: expected proportion of anomalies (0.01 to 0.5)
        - use_ensemble: use ensemble voting (default: true)
    """
    try:
        data = json.loads(request.body)
        contamination = float(data.get('contamination', 0.1))
        use_ensemble = data.get('use_ensemble', True)
        
        incomes = Income.objects.filter(user=request.user)
        expenses = Expense.objects.filter(user=request.user)
        
        detector = AdvancedAnomalyDetector(contamination=contamination)
        result = detector.detect(incomes, expenses, use_ensemble=use_ensemble)
        
        return JsonResponse(result)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(['POST'])
def clustering_api(request):
    """
    Transaction clustering and segmentation
    
    POST params:
        - method: 'kmeans', 'dbscan', 'hierarchical', 'auto'
        - n_clusters: number of clusters (for kmeans/hierarchical)
        - auto_select: automatically find optimal clusters
    """
    try:
        data = json.loads(request.body)
        method = data.get('method', 'auto')
        n_clusters = int(data.get('n_clusters', 5))
        auto_select = data.get('auto_select', True)
        
        incomes = Income.objects.filter(user=request.user)
        expenses = Expense.objects.filter(user=request.user)
        
        clusterer = TransactionClusterer(n_clusters=n_clusters, method=method)
        result = clusterer.cluster(incomes, expenses, auto_select=auto_select)
        
        return JsonResponse(result)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(['POST'])
def train_advanced_classifier_api(request):
    """
    Train advanced expense classifier using ensemble methods
    
    POST params:
        - use_ensemble: use ensemble of models (default: true)
    """
    try:
        data = json.loads(request.body)
        use_ensemble = data.get('use_ensemble', True)
        
        expenses = Expense.objects.filter(user=request.user)
        
        classifier = AdvancedExpenseClassifier(use_ensemble=use_ensemble)
        result = classifier.auto_train_from_db(expenses)
        
        if result.get('success'):
            # Save model for later use
            from pathlib import Path
            from django.conf import settings
            model_path = Path(settings.MEDIA_ROOT) / 'ml' / f'advanced_classifier_{request.user.id}.joblib'
            classifier.save(model_path)
            result['model_saved'] = str(model_path)
        
        return JsonResponse(result)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(['POST'])
def predict_category_api(request):
    """
    Predict expense category with confidence scores
    
    POST params:
        - text: transaction description
    """
    try:
        data = json.loads(request.body)
        text = data.get('text', '')
        
        if not text:
            return JsonResponse({
                'success': False,
                'error': 'Text required'
            }, status=400)
        
        # Try to load user's model
        from pathlib import Path
        from django.conf import settings
        
        model_path = Path(settings.MEDIA_ROOT) / 'ml' / f'advanced_classifier_{request.user.id}.joblib'
        
        if model_path.exists():
            classifier = AdvancedExpenseClassifier.load(model_path)
            prediction = classifier.predict(text)
            probabilities = classifier.predict_proba(text)
        else:
            # Fallback to simple prediction
            classifier = AdvancedExpenseClassifier(use_ensemble=False)
            prediction = classifier._fallback_predict(text)
            probabilities = {}
        
        return JsonResponse({
            'success': True,
            'prediction': prediction,
            'probabilities': probabilities,
            'text': text
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(['POST'])
def monte_carlo_simulation_api(request):
    """
    Monte Carlo simulation for profit forecasting and risk assessment
    
    POST params:
        - n_simulations: number of simulations (default: 1000)
        - days_ahead: days to simulate (default: 30)
    """
    try:
        data = json.loads(request.body)
        n_simulations = int(data.get('n_simulations', 1000))
        days_ahead = int(data.get('days_ahead', 30))
        
        incomes = Income.objects.filter(user=request.user)
        expenses = Expense.objects.filter(user=request.user)
        
        simulator = MonteCarloSimulator(n_simulations=n_simulations)
        result = simulator.simulate_profit(incomes, expenses, days_ahead=days_ahead)
        
        return JsonResponse(result)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(['POST'])
def goal_simulation_api(request):
    """
    Simulate probability of achieving financial goal
    
    POST params:
        - current_balance: current balance
        - target: target amount
        - monthly_income_mean: average monthly income
        - monthly_income_std: income standard deviation
        - monthly_expense_mean: average monthly expense
        - monthly_expense_std: expense standard deviation
        - max_months: maximum months to simulate
    """
    try:
        data = json.loads(request.body)
        
        simulator = MonteCarloSimulator(n_simulations=1000)
        result = simulator.simulate_goal_achievement(
            current_balance=float(data.get('current_balance', 0)),
            target=float(data.get('target', 10000)),
            monthly_income_mean=float(data.get('monthly_income_mean', 5000)),
            monthly_income_std=float(data.get('monthly_income_std', 1000)),
            monthly_expense_mean=float(data.get('monthly_expense_mean', 4000)),
            monthly_expense_std=float(data.get('monthly_expense_std', 800)),
            max_months=int(data.get('max_months', 24))
        )
        
        return JsonResponse(result)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(['GET'])
def time_series_decomposition_api(request):
    """
    Time series decomposition into trend, seasonality, residuals
    
    GET params:
        - period: period for seasonality (default: 7 for weekly)
    """
    try:
        period = int(request.GET.get('period', 7))
        
        incomes = Income.objects.filter(user=request.user)
        expenses = Expense.objects.filter(user=request.user)
        
        analyzer = TimeSeriesAnalyzer()
        result = analyzer.decompose_time_series(incomes, expenses, period=period)
        
        return JsonResponse(result)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(['GET'])
def cohort_analysis_api(request):
    """
    Cohort analysis of transaction patterns
    """
    try:
        incomes = Income.objects.filter(user=request.user)
        expenses = Expense.objects.filter(user=request.user)
        
        analyzer = CohortAnalyzer()
        result = analyzer.analyze_monthly_cohorts(incomes, expenses)
        
        return JsonResponse(result)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(['GET'])
def visualization_sankey_api(request):
    """
    Generate Sankey diagram for cash flow
    """
    try:
        incomes = Income.objects.filter(user=request.user)
        expenses = Expense.objects.filter(user=request.user)
        
        visualizer = AdvancedVisualizer()
        result = visualizer.create_sankey_diagram(incomes, expenses)
        
        return JsonResponse(result)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(['GET'])
def visualization_sunburst_api(request):
    """
    Generate sunburst chart for hierarchical expense breakdown
    """
    try:
        expenses = Expense.objects.filter(user=request.user)
        
        visualizer = AdvancedVisualizer()
        result = visualizer.create_sunburst_chart(expenses)
        
        return JsonResponse(result)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(['GET'])
def visualization_correlation_api(request):
    """
    Generate correlation heatmap
    """
    try:
        incomes = Income.objects.filter(user=request.user)
        expenses = Expense.objects.filter(user=request.user)
        
        visualizer = AdvancedVisualizer()
        result = visualizer.create_correlation_heatmap(incomes, expenses)
        
        return JsonResponse(result)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(['GET'])
def visualization_dashboard_api(request):
    """
    Generate advanced dashboard with multiple charts
    """
    try:
        incomes = Income.objects.filter(user=request.user)
        expenses = Expense.objects.filter(user=request.user)
        
        visualizer = AdvancedVisualizer()
        result = visualizer.create_advanced_dashboard(incomes, expenses)
        
        return JsonResponse(result)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(['GET'])
def ml_metrics_summary_api(request):
    """
    Get summary of all ML capabilities and metrics
    """
    try:
        incomes = Income.objects.filter(user=request.user)
        expenses = Expense.objects.filter(user=request.user)
        
        total_transactions = incomes.count() + expenses.count()
        
        summary = {
            'success': True,
            'data_stats': {
                'total_transactions': total_transactions,
                'n_incomes': incomes.count(),
                'n_expenses': expenses.count(),
                'date_range': {
                    'start': str(min(
                        incomes.order_by('date').first().date if incomes.exists() else datetime.now().date(),
                        expenses.order_by('date').first().date if expenses.exists() else datetime.now().date()
                    )),
                    'end': str(max(
                        incomes.order_by('-date').first().date if incomes.exists() else datetime.now().date(),
                        expenses.order_by('-date').first().date if expenses.exists() else datetime.now().date()
                    ))
                }
            },
            'ml_capabilities': {
                'forecasting': {
                    'available_methods': ['prophet', 'arima', 'lstm', 'ensemble'],
                    'min_data_required': 10,
                    'ready': total_transactions >= 10
                },
                'anomaly_detection': {
                    'available_methods': ['isolation_forest', 'one_class_svm', 'lof', 'dbscan', 'autoencoder', 'statistical'],
                    'min_data_required': 10,
                    'ready': total_transactions >= 10
                },
                'clustering': {
                    'available_methods': ['kmeans', 'dbscan', 'hierarchical'],
                    'min_data_required': 4,
                    'ready': total_transactions >= 4
                },
                'classification': {
                    'available': True,
                    'ensemble_available': True,
                    'min_data_required': 10,
                    'ready': expenses.filter(category__isnull=False).count() >= 10
                },
                'monte_carlo': {
                    'available': True,
                    'min_data_required': 5,
                    'ready': total_transactions >= 5
                },
                'time_series_analysis': {
                    'available': True,
                    'decomposition_available': total_transactions >= 14,
                    'stationarity_tests_available': total_transactions >= 10
                }
            },
            'visualizations': {
                'available': [
                    'sankey_diagram',
                    'sunburst_chart',
                    'correlation_heatmap',
                    'advanced_dashboard',
                    'forecast_chart',
                    'anomaly_scatter',
                    'treemap'
                ]
            }
        }
        
        return JsonResponse(summary)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
