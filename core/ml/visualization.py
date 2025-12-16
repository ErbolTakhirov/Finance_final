"""
Advanced Visualization Module
- Interactive Plotly charts
- Sankey diagrams for cash flow
- Sunburst charts for hierarchical data
- Heatmaps and correlation matrices
- Advanced financial charts
"""

import warnings
from typing import Dict, List, Optional, Any
from datetime import datetime

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    import seaborn as sns
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class AdvancedVisualizer:
    """
    Creates advanced interactive visualizations for financial data
    """
    
    def __init__(self):
        self.theme = 'plotly_dark'  # or 'plotly_white'
        
    def create_sankey_diagram(self, incomes_qs, expenses_qs) -> Dict[str, Any]:
        """
        Create Sankey diagram showing money flow from income sources to expense categories
        
        Returns:
            Plotly figure as JSON
        """
        if not PLOTLY_AVAILABLE:
            return {'success': False, 'error': 'Plotly not available'}
        
        # Aggregate data
        income_by_category = {}
        for inc in incomes_qs:
            cat = inc.category or 'Другие доходы'
            income_by_category[cat] = income_by_category.get(cat, 0) + float(inc.amount)
        
        expense_by_category = {}
        for exp in expenses_qs:
            cat = exp.category or 'Другие расходы'
            expense_by_category[cat] = expense_by_category.get(cat, 0) + float(exp.amount)
        
        if not income_by_category or not expense_by_category:
            return {'success': False, 'error': 'No data available'}
        
        # Build nodes and links
        nodes = list(income_by_category.keys()) + list(expense_by_category.keys()) + ['Общий поток']
        node_indices = {node: i for i, node in enumerate(nodes)}
        
        central_index = node_indices['Общий поток']
        
        sources = []
        targets = []
        values = []
        colors = []
        
        # Income -> Central
        for cat, amount in income_by_category.items():
            sources.append(node_indices[cat])
            targets.append(central_index)
            values.append(amount)
            colors.append('rgba(0, 200, 0, 0.4)')
        
        # Central -> Expenses
        for cat, amount in expense_by_category.items():
            sources.append(central_index)
            targets.append(node_indices[cat])
            values.append(amount)
            colors.append('rgba(200, 0, 0, 0.4)')
        
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color='black', width=0.5),
                label=nodes
            ),
            link=dict(
                source=sources,
                target=targets,
                value=values,
                color=colors
            )
        )])
        
        fig.update_layout(
            title_text="Денежный поток: от доходов к расходам",
            font_size=12
        )
        
        return {
            'success': True,
            'figure_json': fig.to_json()
        }
    
    def create_sunburst_chart(self, expenses_qs, 
                             group_by: str = 'category') -> Dict[str, Any]:
        """
        Create sunburst chart for hierarchical expense breakdown
        
        Args:
            group_by: How to group expenses ('category', 'month')
        
        Returns:
            Plotly figure as JSON
        """
        if not PLOTLY_AVAILABLE:
            return {'success': False, 'error': 'Plotly not available'}
        
        data = []
        for exp in expenses_qs:
            data.append({
                'category': exp.category or 'Другие',
                'amount': float(exp.amount),
                'date': exp.date,
                'description': exp.description or ''
            })
        
        if not data:
            return {'success': False, 'error': 'No data available'}
        
        df = pd.DataFrame(data)
        df['month'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m')
        
        # Create hierarchy: Total -> Month -> Category
        fig = px.sunburst(
            df,
            path=['month', 'category'],
            values='amount',
            title='Иерархия расходов: месяц → категория'
        )
        
        fig.update_traces(textinfo='label+percent parent')
        
        return {
            'success': True,
            'figure_json': fig.to_json()
        }
    
    def create_correlation_heatmap(self, incomes_qs, expenses_qs) -> Dict[str, Any]:
        """
        Create correlation heatmap for different expense categories over time
        
        Returns:
            Plotly figure as JSON
        """
        if not PLOTLY_AVAILABLE:
            return {'success': False, 'error': 'Plotly not available'}
        
        # Prepare data
        data = []
        for exp in expenses_qs:
            data.append({
                'date': exp.date,
                'category': exp.category or 'other',
                'amount': float(exp.amount)
            })
        
        if len(data) < 10:
            return {'success': False, 'error': 'Insufficient data'}
        
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df['month'] = df['date'].dt.to_period('M')
        
        # Pivot: months as rows, categories as columns
        pivot = df.pivot_table(
            index='month',
            columns='category',
            values='amount',
            aggfunc='sum',
            fill_value=0
        )
        
        if pivot.shape[1] < 2:
            return {'success': False, 'error': 'Need at least 2 categories'}
        
        # Calculate correlation
        corr = pivot.corr()
        
        fig = go.Figure(data=go.Heatmap(
            z=corr.values,
            x=corr.columns.tolist(),
            y=corr.columns.tolist(),
            colorscale='RdBu',
            zmid=0,
            text=np.round(corr.values, 2),
            texttemplate='%{text}',
            textfont={"size": 10}
        ))
        
        fig.update_layout(
            title='Корреляция между категориями расходов',
            xaxis_title='Категория',
            yaxis_title='Категория'
        )
        
        return {
            'success': True,
            'figure_json': fig.to_json(),
            'correlation_matrix': corr.to_dict()
        }
    
    def create_advanced_dashboard(self, incomes_qs, expenses_qs) -> Dict[str, Any]:
        """
        Create comprehensive dashboard with multiple subplots
        
        Returns:
            Plotly figure as JSON
        """
        if not PLOTLY_AVAILABLE:
            return {'success': False, 'error': 'Plotly not available'}
        
        # Prepare data
        income_data = [{'date': inc.date, 'amount': float(inc.amount), 'type': 'income'} 
                      for inc in incomes_qs]
        expense_data = [{'date': exp.date, 'amount': float(exp.amount), 'type': 'expense'} 
                       for exp in expenses_qs]
        
        all_data = income_data + expense_data
        if not all_data:
            return {'success': False, 'error': 'No data available'}
        
        df = pd.DataFrame(all_data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Кумулятивная прибыль',
                'Доходы vs Расходы (ежемесячно)',
                'Распределение транзакций',
                'Тренд (скользящее среднее)'
            ),
            specs=[
                [{"type": "scatter"}, {"type": "bar"}],
                [{"type": "histogram"}, {"type": "scatter"}]
            ]
        )
        
        # 1. Cumulative profit
        df_daily = df.groupby('date').apply(
            lambda x: x[x['type'] == 'income']['amount'].sum() - 
                     x[x['type'] == 'expense']['amount'].sum()
        ).reset_index()
        df_daily.columns = ['date', 'profit']
        df_daily['cumulative'] = df_daily['profit'].cumsum()
        
        fig.add_trace(
            go.Scatter(
                x=df_daily['date'],
                y=df_daily['cumulative'],
                mode='lines',
                name='Кумулятивная прибыль',
                fill='tozeroy'
            ),
            row=1, col=1
        )
        
        # 2. Monthly income vs expenses
        df['month'] = df['date'].dt.to_period('M').astype(str)
        monthly = df.groupby(['month', 'type'])['amount'].sum().reset_index()
        monthly_pivot = monthly.pivot(index='month', columns='type', values='amount').fillna(0)
        
        if 'income' in monthly_pivot.columns:
            fig.add_trace(
                go.Bar(x=monthly_pivot.index, y=monthly_pivot['income'], 
                      name='Доходы', marker_color='green'),
                row=1, col=2
            )
        
        if 'expense' in monthly_pivot.columns:
            fig.add_trace(
                go.Bar(x=monthly_pivot.index, y=monthly_pivot['expense'],
                      name='Расходы', marker_color='red'),
                row=1, col=2
            )
        
        # 3. Distribution histogram
        fig.add_trace(
            go.Histogram(
                x=df[df['type'] == 'income']['amount'],
                name='Доходы',
                marker_color='green',
                opacity=0.7
            ),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Histogram(
                x=df[df['type'] == 'expense']['amount'],
                name='Расходы',
                marker_color='red',
                opacity=0.7
            ),
            row=2, col=1
        )
        
        # 4. Moving average trend
        window = min(7, len(df_daily) // 3)
        if window >= 2:
            df_daily['ma'] = df_daily['profit'].rolling(window=window).mean()
            
            fig.add_trace(
                go.Scatter(
                    x=df_daily['date'],
                    y=df_daily['profit'],
                    mode='markers',
                    name='Ежедневная прибыль',
                    marker=dict(size=5, opacity=0.5)
                ),
                row=2, col=2
            )
            
            fig.add_trace(
                go.Scatter(
                    x=df_daily['date'],
                    y=df_daily['ma'],
                    mode='lines',
                    name=f'MA-{window}',
                    line=dict(width=3)
                ),
                row=2, col=2
            )
        
        fig.update_layout(
            height=800,
            showlegend=True,
            title_text="Продвинутая Финансовая Аналитика"
        )
        
        return {
            'success': True,
            'figure_json': fig.to_json()
        }
    
    def create_forecast_chart(self, historical_dates: List[str],
                             historical_values: List[float],
                             forecast_dates: List[str],
                             forecast_values: List[float],
                             lower_bound: Optional[List[float]] = None,
                             upper_bound: Optional[List[float]] = None) -> Dict[str, Any]:
        """
        Create forecast visualization with confidence intervals
        
        Returns:
            Plotly figure as JSON
        """
        if not PLOTLY_AVAILABLE:
            return {'success': False, 'error': 'Plotly not available'}
        
        fig = go.Figure()
        
        # Historical data
        fig.add_trace(go.Scatter(
            x=historical_dates,
            y=historical_values,
            mode='lines+markers',
            name='Исторические данные',
            line=dict(color='blue')
        ))
        
        # Forecast
        fig.add_trace(go.Scatter(
            x=forecast_dates,
            y=forecast_values,
            mode='lines+markers',
            name='Прогноз',
            line=dict(color='red', dash='dash')
        ))
        
        # Confidence intervals
        if lower_bound and upper_bound:
            fig.add_trace(go.Scatter(
                x=forecast_dates + forecast_dates[::-1],
                y=upper_bound + lower_bound[::-1],
                fill='toself',
                fillcolor='rgba(255, 0, 0, 0.2)',
                line=dict(color='rgba(255,255,255,0)'),
                name='95% доверительный интервал',
                showlegend=True
            ))
        
        fig.update_layout(
            title='Прогноз прибыли с доверительными интервалами',
            xaxis_title='Дата',
            yaxis_title='Прибыль',
            hovermode='x unified'
        )
        
        return {
            'success': True,
            'figure_json': fig.to_json()
        }
    
    def create_category_treemap(self, expenses_qs) -> Dict[str, Any]:
        """
        Create treemap visualization of expenses by category
        
        Returns:
            Plotly figure as JSON
        """
        if not PLOTLY_AVAILABLE:
            return {'success': False, 'error': 'Plotly not available'}
        
        data = []
        for exp in expenses_qs:
            data.append({
                'category': exp.category or 'Другие',
                'amount': float(exp.amount)
            })
        
        if not data:
            return {'success': False, 'error': 'No data available'}
        
        df = pd.DataFrame(data)
        category_totals = df.groupby('category')['amount'].sum().reset_index()
        
        fig = px.treemap(
            category_totals,
            path=['category'],
            values='amount',
            title='Структура расходов по категориям'
        )
        
        fig.update_traces(textinfo='label+value+percent parent')
        
        return {
            'success': True,
            'figure_json': fig.to_json()
        }
    
    def create_anomaly_scatter(self, transactions: List[Dict], 
                               anomaly_ids: List[int]) -> Dict[str, Any]:
        """
        Create scatter plot highlighting anomalies
        
        Args:
            transactions: List of transaction dicts with id, date, amount
            anomaly_ids: List of transaction IDs that are anomalies
        
        Returns:
            Plotly figure as JSON
        """
        if not PLOTLY_AVAILABLE:
            return {'success': False, 'error': 'Plotly not available'}
        
        df = pd.DataFrame(transactions)
        df['is_anomaly'] = df['id'].isin(anomaly_ids)
        df['date'] = pd.to_datetime(df['date'])
        
        fig = go.Figure()
        
        # Normal transactions
        normal = df[~df['is_anomaly']]
        fig.add_trace(go.Scatter(
            x=normal['date'],
            y=normal['amount'],
            mode='markers',
            name='Обычные транзакции',
            marker=dict(size=8, color='blue', opacity=0.6)
        ))
        
        # Anomalies
        anomalies = df[df['is_anomaly']]
        fig.add_trace(go.Scatter(
            x=anomalies['date'],
            y=anomalies['amount'],
            mode='markers',
            name='Аномалии',
            marker=dict(size=15, color='red', symbol='x', 
                       line=dict(width=2, color='darkred'))
        ))
        
        fig.update_layout(
            title='Обнаружение аномалий в транзакциях',
            xaxis_title='Дата',
            yaxis_title='Сумма',
            hovermode='closest'
        )
        
        return {
            'success': True,
            'figure_json': fig.to_json()
        }
