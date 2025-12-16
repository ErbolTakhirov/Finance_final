"""
Advanced Analytics Module
- Monte Carlo simulations for risk assessment
- Time series decomposition
- Statistical testing
- Cohort analysis
- Advanced KPI calculations
"""

import warnings
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings('ignore')

try:
    from statsmodels.tsa.seasonal import seasonal_decompose
    from statsmodels.stats.diagnostic import acorr_ljungbox
    from statsmodels.tsa.stattools import adfuller, kpss
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False


class MonteCarloSimulator:
    """
    Monte Carlo simulation for financial forecasting and risk assessment
    """
    
    def __init__(self, n_simulations: int = 1000):
        self.n_simulations = n_simulations
        
    def simulate_profit(self, incomes_qs, expenses_qs, 
                       days_ahead: int = 30) -> Dict[str, Any]:
        """
        Monte Carlo simulation of future profit
        
        Args:
            incomes_qs: Income queryset
            expenses_qs: Expense queryset
            days_ahead: Number of days to simulate
        
        Returns:
            Simulation results with confidence intervals
        """
        # Historical data
        income_amounts = [float(inc.amount) for inc in incomes_qs]
        expense_amounts = [float(exp.amount) for exp in expenses_qs]
        
        if not income_amounts or not expense_amounts:
            return {
                'success': False,
                'error': 'Insufficient data for simulation'
            }
        
        # Calculate historical statistics
        income_mean = np.mean(income_amounts)
        income_std = np.std(income_amounts)
        expense_mean = np.mean(expense_amounts)
        expense_std = np.std(expense_amounts)
        
        # Daily transaction frequency
        income_dates = [inc.date for inc in incomes_qs]
        expense_dates = [exp.date for exp in expenses_qs]
        
        date_range = (max(max(income_dates), max(expense_dates)) - 
                     min(min(income_dates), min(expense_dates))).days + 1
        
        income_freq = len(income_amounts) / max(1, date_range)
        expense_freq = len(expense_amounts) / max(1, date_range)
        
        # Run simulations
        simulations = []
        
        for _ in range(self.n_simulations):
            daily_profit = []
            
            for day in range(days_ahead):
                # Simulate number of transactions
                n_incomes = np.random.poisson(income_freq)
                n_expenses = np.random.poisson(expense_freq)
                
                # Simulate amounts
                day_incomes = np.random.normal(income_mean, income_std, n_incomes)
                day_expenses = np.random.normal(expense_mean, expense_std, n_expenses)
                
                # Ensure non-negative
                day_incomes = np.maximum(day_incomes, 0)
                day_expenses = np.maximum(day_expenses, 0)
                
                daily_profit.append(day_incomes.sum() - day_expenses.sum())
            
            simulations.append(daily_profit)
        
        simulations = np.array(simulations)
        
        # Calculate statistics
        mean_profit = simulations.mean(axis=0)
        median_profit = np.median(simulations, axis=0)
        std_profit = simulations.std(axis=0)
        
        # Confidence intervals
        ci_5 = np.percentile(simulations, 5, axis=0)
        ci_25 = np.percentile(simulations, 25, axis=0)
        ci_75 = np.percentile(simulations, 75, axis=0)
        ci_95 = np.percentile(simulations, 95, axis=0)
        
        # Cumulative profit
        cumulative_simulations = np.cumsum(simulations, axis=1)
        cumulative_mean = cumulative_simulations.mean(axis=0)
        cumulative_ci_5 = np.percentile(cumulative_simulations, 5, axis=0)
        cumulative_ci_95 = np.percentile(cumulative_simulations, 95, axis=0)
        
        # Risk metrics
        final_profits = cumulative_simulations[:, -1]
        prob_profit = (final_profits > 0).mean()
        var_95 = np.percentile(final_profits, 5)  # Value at Risk
        cvar_95 = final_profits[final_profits <= var_95].mean()  # Conditional VaR
        
        return {
            'success': True,
            'n_simulations': self.n_simulations,
            'days_ahead': days_ahead,
            'daily_profit': {
                'mean': mean_profit.tolist(),
                'median': median_profit.tolist(),
                'std': std_profit.tolist(),
                'ci_5': ci_5.tolist(),
                'ci_25': ci_25.tolist(),
                'ci_75': ci_75.tolist(),
                'ci_95': ci_95.tolist()
            },
            'cumulative_profit': {
                'mean': cumulative_mean.tolist(),
                'ci_5': cumulative_ci_5.tolist(),
                'ci_95': cumulative_ci_95.tolist()
            },
            'risk_metrics': {
                'probability_of_profit': float(prob_profit),
                'expected_profit': float(cumulative_mean[-1]),
                'value_at_risk_95': float(var_95),
                'conditional_var_95': float(cvar_95),
                'best_case': float(cumulative_ci_95[-1]),
                'worst_case': float(cumulative_ci_5[-1])
            }
        }
    
    def simulate_goal_achievement(self, current_balance: float, 
                                  target: float,
                                  monthly_income_mean: float,
                                  monthly_income_std: float,
                                  monthly_expense_mean: float,
                                  monthly_expense_std: float,
                                  max_months: int = 24) -> Dict[str, Any]:
        """
        Simulate probability and time to achieve financial goal
        
        Returns:
            Goal achievement statistics
        """
        achievements = []
        months_to_goal = []
        
        for _ in range(self.n_simulations):
            balance = current_balance
            
            for month in range(max_months):
                monthly_income = max(0, np.random.normal(monthly_income_mean, monthly_income_std))
                monthly_expense = max(0, np.random.normal(monthly_expense_mean, monthly_expense_std))
                
                balance += monthly_income - monthly_expense
                
                if balance >= target:
                    achievements.append(True)
                    months_to_goal.append(month + 1)
                    break
            else:
                achievements.append(False)
                months_to_goal.append(max_months)
        
        success_rate = np.mean(achievements)
        avg_months = np.mean(months_to_goal)
        median_months = np.median(months_to_goal)
        
        return {
            'success': True,
            'target': target,
            'current_balance': current_balance,
            'probability_of_achievement': float(success_rate),
            'expected_months_to_goal': float(avg_months),
            'median_months_to_goal': float(median_months),
            'percentiles': {
                '10': float(np.percentile(months_to_goal, 10)),
                '25': float(np.percentile(months_to_goal, 25)),
                '50': float(np.percentile(months_to_goal, 50)),
                '75': float(np.percentile(months_to_goal, 75)),
                '90': float(np.percentile(months_to_goal, 90))
            }
        }


class TimeSeriesAnalyzer:
    """
    Advanced time series analysis and decomposition
    """
    
    def decompose_time_series(self, incomes_qs, expenses_qs, 
                              period: int = 7) -> Dict[str, Any]:
        """
        Decompose time series into trend, seasonality, and residuals
        
        Args:
            period: Period for seasonal decomposition (7 for weekly, 30 for monthly)
        
        Returns:
            Decomposition results
        """
        if not STATSMODELS_AVAILABLE:
            return {
                'success': False,
                'error': 'statsmodels not available'
            }
        
        # Prepare daily time series
        data = []
        for inc in incomes_qs:
            data.append({'date': inc.date, 'amount': float(inc.amount)})
        for exp in expenses_qs:
            data.append({'date': exp.date, 'amount': -float(exp.amount)})
        
        if len(data) < period * 2:
            return {
                'success': False,
                'error': f'Need at least {period * 2} data points for decomposition'
            }
        
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        
        # Resample to regular frequency
        daily_profit = df.set_index('date').resample('D')['amount'].sum()
        daily_profit = daily_profit.fillna(0)
        
        try:
            # Perform decomposition
            decomposition = seasonal_decompose(
                daily_profit, 
                model='additive', 
                period=period,
                extrapolate_trend='freq'
            )
            
            dates = daily_profit.index.strftime('%Y-%m-%d').tolist()
            
            return {
                'success': True,
                'dates': dates,
                'original': daily_profit.values.tolist(),
                'trend': decomposition.trend.fillna(0).values.tolist(),
                'seasonal': decomposition.seasonal.fillna(0).values.tolist(),
                'residual': decomposition.resid.fillna(0).values.tolist(),
                'period': period
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': f'Decomposition failed: {str(e)}'
            }
    
    def test_stationarity(self, time_series: np.ndarray) -> Dict[str, Any]:
        """
        Test if time series is stationary using ADF and KPSS tests
        
        Returns:
            Stationarity test results
        """
        if not STATSMODELS_AVAILABLE:
            return {'success': False, 'error': 'statsmodels not available'}
        
        try:
            # Augmented Dickey-Fuller test
            adf_result = adfuller(time_series)
            
            # KPSS test
            kpss_result = kpss(time_series, regression='c')
            
            return {
                'success': True,
                'adf_test': {
                    'statistic': float(adf_result[0]),
                    'p_value': float(adf_result[1]),
                    'is_stationary': adf_result[1] < 0.05
                },
                'kpss_test': {
                    'statistic': float(kpss_result[0]),
                    'p_value': float(kpss_result[1]),
                    'is_stationary': kpss_result[1] > 0.05
                }
            }
        
        except Exception as e:
            return {'success': False, 'error': str(e)}


class CohortAnalyzer:
    """
    Cohort analysis for transaction patterns
    """
    
    def analyze_monthly_cohorts(self, incomes_qs, expenses_qs) -> Dict[str, Any]:
        """
        Analyze transaction cohorts by month
        
        Returns:
            Cohort retention and spending patterns
        """
        data = []
        
        for inc in incomes_qs:
            data.append({
                'date': inc.date,
                'type': 'income',
                'amount': float(inc.amount),
                'category': inc.category or 'unknown'
            })
        
        for exp in expenses_qs:
            data.append({
                'date': exp.date,
                'type': 'expense',
                'amount': float(exp.amount),
                'category': exp.category or 'unknown'
            })
        
        if not data:
            return {'success': False, 'error': 'No data available'}
        
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df['cohort_month'] = df['date'].dt.to_period('M')
        
        # Cohort statistics
        cohorts = df.groupby(['cohort_month', 'type']).agg({
            'amount': ['sum', 'mean', 'count']
        }).reset_index()
        
        cohort_data = []
        for _, row in cohorts.iterrows():
            cohort_data.append({
                'month': str(row['cohort_month']),
                'type': row['type'],
                'total_amount': float(row['amount']['sum']),
                'avg_amount': float(row['amount']['mean']),
                'n_transactions': int(row['amount']['count'])
            })
        
        # Month-over-month growth
        monthly_totals = df.groupby('cohort_month')['amount'].sum().sort_index()
        mom_growth = monthly_totals.pct_change() * 100
        
        return {
            'success': True,
            'cohort_data': cohort_data,
            'mom_growth': {
                'months': [str(m) for m in mom_growth.index],
                'growth_rate': mom_growth.fillna(0).values.tolist()
            }
        }


class StatisticalTester:
    """
    Statistical hypothesis testing for financial data
    """
    
    def compare_periods(self, period1_data: List[float], 
                       period2_data: List[float]) -> Dict[str, Any]:
        """
        Compare two time periods using statistical tests
        
        Returns:
            Test results with p-values
        """
        if len(period1_data) < 2 or len(period2_data) < 2:
            return {'success': False, 'error': 'Insufficient data for comparison'}
        
        # T-test
        t_stat, t_pval = stats.ttest_ind(period1_data, period2_data)
        
        # Mann-Whitney U test (non-parametric)
        u_stat, u_pval = stats.mannwhitneyu(period1_data, period2_data)
        
        # Effect size (Cohen's d)
        mean1, mean2 = np.mean(period1_data), np.mean(period2_data)
        std_pooled = np.sqrt((np.var(period1_data) + np.var(period2_data)) / 2)
        cohens_d = (mean1 - mean2) / std_pooled if std_pooled > 0 else 0
        
        return {
            'success': True,
            'period1_stats': {
                'mean': float(mean1),
                'median': float(np.median(period1_data)),
                'std': float(np.std(period1_data)),
                'n': len(period1_data)
            },
            'period2_stats': {
                'mean': float(mean2),
                'median': float(np.median(period2_data)),
                'std': float(np.std(period2_data)),
                'n': len(period2_data)
            },
            'tests': {
                't_test': {
                    'statistic': float(t_stat),
                    'p_value': float(t_pval),
                    'significant': t_pval < 0.05
                },
                'mann_whitney': {
                    'statistic': float(u_stat),
                    'p_value': float(u_pval),
                    'significant': u_pval < 0.05
                },
                'effect_size': {
                    'cohens_d': float(cohens_d),
                    'interpretation': self._interpret_cohens_d(cohens_d)
                }
            }
        }
    
    def _interpret_cohens_d(self, d: float) -> str:
        """Interpret Cohen's d effect size"""
        abs_d = abs(d)
        if abs_d < 0.2:
            return 'negligible'
        elif abs_d < 0.5:
            return 'small'
        elif abs_d < 0.8:
            return 'medium'
        else:
            return 'large'
