"""
Advanced Anomaly Detection Module
Implements multiple anomaly detection algorithms:
- Isolation Forest
- One-Class SVM
- Local Outlier Factor
- Autoencoder Neural Network
- Statistical methods (Z-score, IQR, DBSCAN)
"""

import warnings
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
from sklearn.svm import OneClassSVM
from sklearn.neighbors import LocalOutlierFactor
from sklearn.cluster import DBSCAN
from datetime import datetime, timedelta

warnings.filterwarnings('ignore')

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
    
    class AutoencoderAnomalyDetector(nn.Module):
        """Autoencoder neural network for anomaly detection"""
        
        def __init__(self, input_dim: int, encoding_dim: int = 8):
            super(AutoencoderAnomalyDetector, self).__init__()
            
            # Encoder
            self.encoder = nn.Sequential(
                nn.Linear(input_dim, 32),
                nn.ReLU(),
                nn.Linear(32, 16),
                nn.ReLU(),
                nn.Linear(16, encoding_dim),
                nn.ReLU()
            )
            
            # Decoder
            self.decoder = nn.Sequential(
                nn.Linear(encoding_dim, 16),
                nn.ReLU(),
                nn.Linear(16, 32),
                nn.ReLU(),
                nn.Linear(32, input_dim)
            )
        
        def forward(self, x):
            encoded = self.encoder(x)
            decoded = self.decoder(encoded)
            return decoded
            
except ImportError:
    TORCH_AVAILABLE = False
    
    class AutoencoderAnomalyDetector:
        """Autoencoder neural network for anomaly detection (dummy when PyTorch not available)"""
        
        def __init__(self, *args, **kwargs):
            pass


class AdvancedAnomalyDetector:
    """
    Advanced anomaly detection system combining multiple algorithms.
    Uses ensemble voting for robust detection.
    """
    
    def __init__(self, contamination: float = 0.1):
        """
        Args:
            contamination: Expected proportion of anomalies (0.0 to 0.5)
        """
        self.contamination = contamination
        self.scaler = StandardScaler()
        self.models = {}
        self.thresholds = {}
        
    def prepare_features(self, transactions_df: pd.DataFrame) -> pd.DataFrame:
        """Extract features from transaction data"""
        df = transactions_df.copy()
        
        # Basic features
        df['amount_abs'] = df['amount'].abs()
        df['log_amount'] = np.log1p(df['amount_abs'])
        
        # Temporal features
        df['day_of_week'] = df['date'].dt.dayofweek
        df['day_of_month'] = df['date'].dt.day
        df['month'] = df['date'].dt.month
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
        
        # Statistical features
        df['z_score'] = (df['amount'] - df['amount'].mean()) / df['amount'].std()
        
        # Rolling statistics (if enough data)
        if len(df) >= 7:
            df['rolling_mean_7d'] = df['amount'].rolling(window=7, min_periods=1).mean()
            df['rolling_std_7d'] = df['amount'].rolling(window=7, min_periods=1).std()
            df['deviation_from_mean'] = (df['amount'] - df['rolling_mean_7d']) / (df['rolling_std_7d'] + 1e-8)
        else:
            df['rolling_mean_7d'] = df['amount'].mean()
            df['rolling_std_7d'] = df['amount'].std()
            df['deviation_from_mean'] = 0
        
        # Category frequency encoding
        if 'category' in df.columns:
            category_freq = df['category'].value_counts(normalize=True)
            df['category_freq'] = df['category'].map(category_freq)
        else:
            df['category_freq'] = 1.0
        
        return df
    
    def detect_statistical_anomalies(self, df: pd.DataFrame, 
                                    z_threshold: float = 3.0,
                                    iqr_multiplier: float = 1.5) -> Dict[str, Any]:
        """Statistical anomaly detection using Z-score and IQR"""
        anomalies = []
        
        # Z-score method
        mean = df['amount'].mean()
        std = df['amount'].std()
        z_scores = np.abs((df['amount'] - mean) / (std + 1e-8))
        z_anomalies = df[z_scores > z_threshold].index.tolist()
        
        # IQR method
        Q1 = df['amount'].quantile(0.25)
        Q3 = df['amount'].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - iqr_multiplier * IQR
        upper_bound = Q3 + iqr_multiplier * IQR
        iqr_anomalies = df[(df['amount'] < lower_bound) | (df['amount'] > upper_bound)].index.tolist()
        
        # Combine both methods
        combined_anomalies = list(set(z_anomalies + iqr_anomalies))
        
        return {
            'method': 'statistical',
            'anomaly_indices': combined_anomalies,
            'z_score_threshold': z_threshold,
            'iqr_bounds': {'lower': float(lower_bound), 'upper': float(upper_bound)},
            'n_anomalies': len(combined_anomalies)
        }
    
    def detect_isolation_forest(self, X: np.ndarray) -> Dict[str, Any]:
        """Isolation Forest anomaly detection"""
        try:
            model = IsolationForest(
                contamination=self.contamination,
                random_state=42,
                n_estimators=100
            )
            predictions = model.fit_predict(X)
            anomaly_scores = model.score_samples(X)
            
            anomaly_indices = np.where(predictions == -1)[0].tolist()
            
            self.models['isolation_forest'] = model
            
            return {
                'method': 'isolation_forest',
                'anomaly_indices': anomaly_indices,
                'anomaly_scores': anomaly_scores.tolist(),
                'n_anomalies': len(anomaly_indices)
            }
        except Exception as e:
            print(f"Isolation Forest error: {e}")
            return None
    
    def detect_one_class_svm(self, X: np.ndarray) -> Dict[str, Any]:
        """One-Class SVM anomaly detection"""
        try:
            model = OneClassSVM(
                nu=self.contamination,
                kernel='rbf',
                gamma='auto'
            )
            predictions = model.fit_predict(X)
            
            anomaly_indices = np.where(predictions == -1)[0].tolist()
            
            self.models['one_class_svm'] = model
            
            return {
                'method': 'one_class_svm',
                'anomaly_indices': anomaly_indices,
                'n_anomalies': len(anomaly_indices)
            }
        except Exception as e:
            print(f"One-Class SVM error: {e}")
            return None
    
    def detect_local_outlier_factor(self, X: np.ndarray) -> Dict[str, Any]:
        """Local Outlier Factor anomaly detection"""
        try:
            model = LocalOutlierFactor(
                contamination=self.contamination,
                novelty=False
            )
            predictions = model.fit_predict(X)
            outlier_scores = model.negative_outlier_factor_
            
            anomaly_indices = np.where(predictions == -1)[0].tolist()
            
            return {
                'method': 'local_outlier_factor',
                'anomaly_indices': anomaly_indices,
                'outlier_scores': outlier_scores.tolist(),
                'n_anomalies': len(anomaly_indices)
            }
        except Exception as e:
            print(f"LOF error: {e}")
            return None
    
    def detect_dbscan_clusters(self, X: np.ndarray) -> Dict[str, Any]:
        """DBSCAN clustering-based anomaly detection"""
        try:
            model = DBSCAN(eps=0.5, min_samples=5)
            clusters = model.fit_predict(X)
            
            # Points labeled as -1 are anomalies
            anomaly_indices = np.where(clusters == -1)[0].tolist()
            
            return {
                'method': 'dbscan',
                'anomaly_indices': anomaly_indices,
                'clusters': clusters.tolist(),
                'n_clusters': len(set(clusters)) - (1 if -1 in clusters else 0),
                'n_anomalies': len(anomaly_indices)
            }
        except Exception as e:
            print(f"DBSCAN error: {e}")
            return None
    
    def detect_autoencoder(self, X: np.ndarray, epochs: int = 50,
                          reconstruction_threshold_percentile: float = 95) -> Dict[str, Any]:
        """Autoencoder-based anomaly detection"""
        if not TORCH_AVAILABLE or len(X) < 20:
            return None
        
        try:
            # Prepare data
            X_tensor = torch.FloatTensor(X)
            
            # Create and train autoencoder
            input_dim = X.shape[1]
            model = AutoencoderAnomalyDetector(input_dim=input_dim, encoding_dim=max(2, input_dim // 4))
            
            criterion = nn.MSELoss()
            optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
            
            model.train()
            for epoch in range(epochs):
                optimizer.zero_grad()
                reconstructed = model(X_tensor)
                loss = criterion(reconstructed, X_tensor)
                loss.backward()
                optimizer.step()
            
            # Calculate reconstruction errors
            model.eval()
            with torch.no_grad():
                reconstructed = model(X_tensor)
                reconstruction_errors = torch.mean((X_tensor - reconstructed) ** 2, dim=1).numpy()
            
            # Determine threshold based on percentile
            threshold = np.percentile(reconstruction_errors, reconstruction_threshold_percentile)
            anomaly_indices = np.where(reconstruction_errors > threshold)[0].tolist()
            
            self.models['autoencoder'] = model
            self.thresholds['autoencoder'] = threshold
            
            return {
                'method': 'autoencoder',
                'anomaly_indices': anomaly_indices,
                'reconstruction_errors': reconstruction_errors.tolist(),
                'threshold': float(threshold),
                'n_anomalies': len(anomaly_indices)
            }
        except Exception as e:
            print(f"Autoencoder error: {e}")
            return None
    
    def detect(self, incomes_qs, expenses_qs, use_ensemble: bool = True) -> Dict[str, Any]:
        """
        Main anomaly detection method
        
        Args:
            incomes_qs: Django queryset of incomes
            expenses_qs: Django queryset of expenses
            use_ensemble: Use ensemble voting across multiple methods
        
        Returns:
            Dictionary with anomaly detection results
        """
        # Prepare data
        data = []
        for income in incomes_qs:
            data.append({
                'id': income.id,
                'type': 'income',
                'date': income.date,
                'amount': float(income.amount),
                'category': income.category or 'unknown',
                'description': income.description or ''
            })
        
        for expense in expenses_qs:
            data.append({
                'id': expense.id,
                'type': 'expense',
                'date': expense.date,
                'amount': -float(expense.amount),  # Negative for expenses
                'category': expense.category or 'unknown',
                'description': expense.description or ''
            })
        
        if len(data) < 10:
            return {
                'success': False,
                'error': 'Insufficient data for anomaly detection (need at least 10 transactions)'
            }
        
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # Extract features
        df_features = self.prepare_features(df)
        
        # Select numerical features for ML models
        feature_cols = ['amount_abs', 'log_amount', 'day_of_week', 'day_of_month', 
                       'month', 'is_weekend', 'z_score', 'rolling_mean_7d', 
                       'rolling_std_7d', 'deviation_from_mean', 'category_freq']
        
        X = df_features[feature_cols].fillna(0).values
        X_scaled = self.scaler.fit_transform(X)
        
        results = {}
        
        # Statistical methods
        stat_result = self.detect_statistical_anomalies(df_features)
        if stat_result:
            results['statistical'] = stat_result
        
        # Machine learning methods
        if use_ensemble:
            iso_result = self.detect_isolation_forest(X_scaled)
            if iso_result:
                results['isolation_forest'] = iso_result
            
            svm_result = self.detect_one_class_svm(X_scaled)
            if svm_result:
                results['one_class_svm'] = svm_result
            
            lof_result = self.detect_local_outlier_factor(X_scaled)
            if lof_result:
                results['local_outlier_factor'] = lof_result
            
            dbscan_result = self.detect_dbscan_clusters(X_scaled)
            if dbscan_result:
                results['dbscan'] = dbscan_result
            
            ae_result = self.detect_autoencoder(X_scaled)
            if ae_result:
                results['autoencoder'] = ae_result
        
        if not results:
            return {
                'success': False,
                'error': 'All anomaly detection methods failed'
            }
        
        # Ensemble voting: transaction is anomaly if detected by majority of methods
        if use_ensemble and len(results) > 1:
            all_indices = set()
            vote_counts = {}
            
            for method_result in results.values():
                indices = method_result.get('anomaly_indices', [])
                all_indices.update(indices)
                for idx in indices:
                    vote_counts[idx] = vote_counts.get(idx, 0) + 1
            
            # Anomaly if voted by at least half of methods
            min_votes = len(results) // 2 + 1
            ensemble_anomalies = [idx for idx, votes in vote_counts.items() if votes >= min_votes]
        else:
            # Use best single method (isolation forest preferred)
            best_method = results.get('isolation_forest') or results.get('statistical')
            ensemble_anomalies = best_method.get('anomaly_indices', [])
        
        # Prepare detailed anomaly information
        anomalies_detail = []
        for idx in ensemble_anomalies:
            transaction = df.iloc[idx]
            
            # Count how many methods detected this
            detection_count = sum(
                1 for result in results.values()
                if idx in result.get('anomaly_indices', [])
            )
            
            anomalies_detail.append({
                'id': int(transaction['id']),
                'type': transaction['type'],
                'date': transaction['date'].strftime('%Y-%m-%d'),
                'amount': float(transaction['amount']),
                'category': transaction['category'],
                'description': transaction['description'],
                'detection_count': detection_count,
                'total_methods': len(results),
                'confidence': detection_count / len(results)
            })
        
        # Sort by confidence
        anomalies_detail.sort(key=lambda x: x['confidence'], reverse=True)
        
        return {
            'success': True,
            'total_transactions': len(df),
            'n_anomalies': len(ensemble_anomalies),
            'anomaly_percentage': len(ensemble_anomalies) / len(df) * 100,
            'anomalies': anomalies_detail,
            'methods_used': list(results.keys()),
            'individual_results': {k: v['n_anomalies'] for k, v in results.items()}
        }
