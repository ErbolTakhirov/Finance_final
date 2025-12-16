"""
Advanced Time Series Forecasting Module
Implements multiple state-of-the-art forecasting algorithms:
- Prophet (Facebook's time series forecasting)
- ARIMA/SARIMAX (Statistical approach)
- LSTM (Deep Learning approach)
- Ensemble methods combining multiple models
"""

import warnings
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

warnings.filterwarnings('ignore')

try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False

try:
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    from statsmodels.tsa.arima.model import ARIMA
    import pmdarima as pm
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
    
    class LSTMForecaster(nn.Module):
        """LSTM Neural Network for time series forecasting"""
        
        def __init__(self, input_size: int = 1, hidden_size: int = 64, num_layers: int = 2, dropout: float = 0.2):
            super(LSTMForecaster, self).__init__()
            self.hidden_size = hidden_size
            self.num_layers = num_layers
            
            self.lstm = nn.LSTM(
                input_size=input_size,
                hidden_size=hidden_size,
                num_layers=num_layers,
                dropout=dropout if num_layers > 1 else 0,
                batch_first=True
            )
            self.fc = nn.Linear(hidden_size, 1)
            
        def forward(self, x):
            lstm_out, _ = self.lstm(x)
            predictions = self.fc(lstm_out[:, -1, :])
            return predictions
            
except ImportError:
    TORCH_AVAILABLE = False
    
    # Dummy class when torch is not available
    class LSTMForecaster:
        """LSTM Neural Network for time series forecasting (dummy when PyTorch not available)"""
        
        def __init__(self, *args, **kwargs):
            pass


class AdvancedForecaster:
    """
    Advanced forecasting system combining multiple algorithms.
    Automatically selects the best model based on data characteristics.
    """
    
    def __init__(self, method: str = 'auto'):
        """
        Args:
            method: 'auto', 'prophet', 'arima', 'lstm', 'ensemble'
        """
        self.method = method
        self.models = {}
        self.best_model = None
        self.metrics = {}
        
    def prepare_data(self, incomes_qs, expenses_qs) -> pd.DataFrame:
        """Convert Django querysets to time series DataFrame"""
        data = []
        
        for income in incomes_qs:
            data.append({
                'date': income.date,
                'amount': float(income.amount),
                'type': 'income',
                'category': income.category
            })
            
        for expense in expenses_qs:
            data.append({
                'date': expense.date,
                'amount': -float(expense.amount),
                'type': 'expense',
                'category': expense.category
            })
            
        if not data:
            return pd.DataFrame()
            
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        
        # Aggregate by day
        daily_profit = df.groupby('date')['amount'].sum().reset_index()
        daily_profit.columns = ['ds', 'y']
        daily_profit = daily_profit.sort_values('ds')
        
        return daily_profit
    
    def _forecast_prophet(self, df: pd.DataFrame, periods: int = 30) -> Dict[str, Any]:
        """Prophet forecasting"""
        if not PROPHET_AVAILABLE or len(df) < 10:
            return None
            
        try:
            model = Prophet(
                daily_seasonality=True,
                weekly_seasonality=True,
                yearly_seasonality=True if len(df) > 365 else False,
                changepoint_prior_scale=0.05,
                interval_width=0.95
            )
            
            model.fit(df)
            
            future = model.make_future_dataframe(periods=periods)
            forecast = model.predict(future)
            
            # Calculate metrics on training data
            train_pred = forecast[forecast['ds'].isin(df['ds'])]['yhat'].values
            train_actual = df['y'].values
            
            mae = mean_absolute_error(train_actual, train_pred)
            rmse = np.sqrt(mean_squared_error(train_actual, train_pred))
            r2 = r2_score(train_actual, train_pred)
            
            # Get future predictions
            future_forecast = forecast[~forecast['ds'].isin(df['ds'])].tail(periods)
            
            return {
                'model': model,
                'forecast': future_forecast,
                'predictions': future_forecast['yhat'].tolist(),
                'lower_bound': future_forecast['yhat_lower'].tolist(),
                'upper_bound': future_forecast['yhat_upper'].tolist(),
                'dates': future_forecast['ds'].dt.strftime('%Y-%m-%d').tolist(),
                'metrics': {
                    'mae': float(mae),
                    'rmse': float(rmse),
                    'r2': float(r2)
                }
            }
        except Exception as e:
            print(f"Prophet error: {e}")
            return None
    
    def _forecast_arima(self, df: pd.DataFrame, periods: int = 30) -> Dict[str, Any]:
        """ARIMA/Auto-ARIMA forecasting"""
        if not STATSMODELS_AVAILABLE or len(df) < 10:
            return None
            
        try:
            # Auto ARIMA to find best parameters
            model = pm.auto_arima(
                df['y'].values,
                start_p=1, start_q=1,
                max_p=5, max_q=5,
                seasonal=True if len(df) > 30 else False,
                m=7 if len(df) > 30 else 1,  # Weekly seasonality
                stepwise=True,
                suppress_warnings=True,
                error_action='ignore',
                trace=False
            )
            
            # Forecast
            forecast, conf_int = model.predict(n_periods=periods, return_conf_int=True)
            
            # Calculate metrics
            fitted = model.predict_in_sample()
            mae = mean_absolute_error(df['y'].values, fitted)
            rmse = np.sqrt(mean_squared_error(df['y'].values, fitted))
            r2 = r2_score(df['y'].values, fitted)
            
            # Generate future dates
            last_date = df['ds'].max()
            future_dates = pd.date_range(start=last_date + timedelta(days=1), periods=periods, freq='D')
            
            return {
                'model': model,
                'predictions': forecast.tolist(),
                'lower_bound': conf_int[:, 0].tolist(),
                'upper_bound': conf_int[:, 1].tolist(),
                'dates': future_dates.strftime('%Y-%m-%d').tolist(),
                'metrics': {
                    'mae': float(mae),
                    'rmse': float(rmse),
                    'r2': float(r2)
                },
                'order': model.order,
                'seasonal_order': model.seasonal_order
            }
        except Exception as e:
            print(f"ARIMA error: {e}")
            return None
    
    def _forecast_lstm(self, df: pd.DataFrame, periods: int = 30, 
                       sequence_length: int = 14, epochs: int = 50) -> Dict[str, Any]:
        """LSTM Neural Network forecasting"""
        if not TORCH_AVAILABLE or len(df) < sequence_length + 10:
            return None
            
        try:
            # Prepare sequences
            values = df['y'].values
            scaler_mean = values.mean()
            scaler_std = values.std() + 1e-8
            scaled_values = (values - scaler_mean) / scaler_std
            
            X, y = [], []
            for i in range(len(scaled_values) - sequence_length):
                X.append(scaled_values[i:i+sequence_length])
                y.append(scaled_values[i+sequence_length])
            
            X = torch.FloatTensor(X).unsqueeze(-1)
            y = torch.FloatTensor(y).unsqueeze(-1)
            
            # Train model
            model = LSTMForecaster(input_size=1, hidden_size=64, num_layers=2, dropout=0.2)
            criterion = nn.MSELoss()
            optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
            
            model.train()
            for epoch in range(epochs):
                optimizer.zero_grad()
                outputs = model(X)
                loss = criterion(outputs, y)
                loss.backward()
                optimizer.step()
            
            # Generate predictions
            model.eval()
            predictions = []
            current_sequence = scaled_values[-sequence_length:].tolist()
            
            with torch.no_grad():
                for _ in range(periods):
                    seq_tensor = torch.FloatTensor([current_sequence]).unsqueeze(-1)
                    pred = model(seq_tensor).item()
                    predictions.append(pred)
                    current_sequence = current_sequence[1:] + [pred]
            
            # Denormalize
            predictions = [p * scaler_std + scaler_mean for p in predictions]
            
            # Calculate metrics
            with torch.no_grad():
                train_pred = model(X).numpy().flatten()
                train_pred = train_pred * scaler_std + scaler_mean
                train_actual = y.numpy().flatten() * scaler_std + scaler_mean
                
                mae = mean_absolute_error(train_actual, train_pred)
                rmse = np.sqrt(mean_squared_error(train_actual, train_pred))
                r2 = r2_score(train_actual, train_pred)
            
            # Generate future dates
            last_date = df['ds'].max()
            future_dates = pd.date_range(start=last_date + timedelta(days=1), periods=periods, freq='D')
            
            # Confidence intervals (using training error)
            std_error = rmse
            lower_bound = [p - 1.96 * std_error for p in predictions]
            upper_bound = [p + 1.96 * std_error for p in predictions]
            
            return {
                'model': model,
                'predictions': predictions,
                'lower_bound': lower_bound,
                'upper_bound': upper_bound,
                'dates': future_dates.strftime('%Y-%m-%d').tolist(),
                'metrics': {
                    'mae': float(mae),
                    'rmse': float(rmse),
                    'r2': float(r2)
                }
            }
        except Exception as e:
            print(f"LSTM error: {e}")
            return None
    
    def forecast(self, incomes_qs, expenses_qs, periods: int = 30) -> Dict[str, Any]:
        """
        Main forecasting method that selects and runs the best model
        """
        df = self.prepare_data(incomes_qs, expenses_qs)
        
        if df.empty or len(df) < 5:
            return {
                'success': False,
                'error': 'Insufficient data for forecasting',
                'predictions': [],
                'method': 'none'
            }
        
        results = {}
        
        # Try all available methods
        if self.method in ['auto', 'prophet']:
            prophet_result = self._forecast_prophet(df, periods)
            if prophet_result:
                results['prophet'] = prophet_result
        
        if self.method in ['auto', 'arima']:
            arima_result = self._forecast_arima(df, periods)
            if arima_result:
                results['arima'] = arima_result
        
        if self.method in ['auto', 'lstm']:
            lstm_result = self._forecast_lstm(df, periods)
            if lstm_result:
                results['lstm'] = lstm_result
        
        if not results:
            # Fallback to simple linear regression
            from sklearn.linear_model import LinearRegression
            X = np.arange(len(df)).reshape(-1, 1)
            y = df['y'].values
            model = LinearRegression()
            model.fit(X, y)
            
            future_X = np.arange(len(df), len(df) + periods).reshape(-1, 1)
            predictions = model.predict(future_X).tolist()
            
            last_date = df['ds'].max()
            future_dates = pd.date_range(start=last_date + timedelta(days=1), periods=periods, freq='D')
            
            return {
                'success': True,
                'method': 'linear_regression',
                'predictions': predictions,
                'dates': future_dates.strftime('%Y-%m-%d').tolist(),
                'confidence': 'low'
            }
        
        # Select best model based on R² score
        best_method = max(results.keys(), key=lambda k: results[k]['metrics'].get('r2', -999))
        best_result = results[best_method]
        
        # Ensemble prediction (average of all models)
        if self.method == 'ensemble' and len(results) > 1:
            ensemble_pred = np.mean([r['predictions'] for r in results.values()], axis=0).tolist()
            ensemble_lower = np.mean([r['lower_bound'] for r in results.values()], axis=0).tolist()
            ensemble_upper = np.mean([r['upper_bound'] for r in results.values()], axis=0).tolist()
            
            return {
                'success': True,
                'method': 'ensemble',
                'models_used': list(results.keys()),
                'predictions': ensemble_pred,
                'lower_bound': ensemble_lower,
                'upper_bound': ensemble_upper,
                'dates': best_result['dates'],
                'individual_results': {k: v['predictions'] for k, v in results.items()},
                'metrics': {k: v['metrics'] for k, v in results.items()}
            }
        
        return {
            'success': True,
            'method': best_method,
            'predictions': best_result['predictions'],
            'lower_bound': best_result.get('lower_bound', []),
            'upper_bound': best_result.get('upper_bound', []),
            'dates': best_result['dates'],
            'metrics': best_result['metrics'],
            'all_methods_tested': list(results.keys())
        }
    
    def get_monthly_forecast(self, incomes_qs, expenses_qs, months: int = 6) -> Dict[str, Any]:
        """Get monthly aggregated forecast"""
        result = self.forecast(incomes_qs, expenses_qs, periods=months * 30)
        
        if not result.get('success'):
            return result
        
        # Aggregate daily predictions to monthly
        dates = pd.to_datetime(result['dates'])
        predictions = result['predictions']
        
        df = pd.DataFrame({'date': dates, 'value': predictions})
        df['month'] = df['date'].dt.to_period('M')
        
        monthly = df.groupby('month')['value'].sum().reset_index()
        monthly['date'] = monthly['month'].dt.to_timestamp()
        
        result['monthly_predictions'] = monthly['value'].tolist()
        result['monthly_dates'] = monthly['date'].dt.strftime('%Y-%m').tolist()
        
        return result
