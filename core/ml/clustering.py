"""
Advanced Clustering and Segmentation Module
- Customer/Transaction segmentation
- Spending pattern analysis
- Behavioral clustering
"""

import warnings
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score, calinski_harabasz_score

warnings.filterwarnings('ignore')

try:
    from sklearn.manifold import TSNE
    import umap
    UMAP_AVAILABLE = True
except ImportError:
    UMAP_AVAILABLE = False


class TransactionClusterer:
    """
    Advanced clustering for transaction segmentation and pattern discovery
    """
    
    def __init__(self, n_clusters: int = 5, method: str = 'kmeans'):
        """
        Args:
            n_clusters: Number of clusters (for methods that need it)
            method: 'kmeans', 'dbscan', 'hierarchical', 'auto'
        """
        self.n_clusters = n_clusters
        self.method = method
        self.scaler = StandardScaler()
        self.model = None
        self.pca = None
        self.labels = None
        self.cluster_centers = None
        
    def extract_features(self, incomes_qs, expenses_qs) -> Tuple[pd.DataFrame, np.ndarray]:
        """Extract features from transactions for clustering"""
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
                'amount': float(expense.amount),
                'category': expense.category or 'unknown',
                'description': expense.description or ''
            })
        
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        
        # Feature engineering
        df['amount_log'] = np.log1p(df['amount'])
        df['day_of_week'] = df['date'].dt.dayofweek
        df['day_of_month'] = df['date'].dt.day
        df['month'] = df['date'].dt.month
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
        df['is_expense'] = (df['type'] == 'expense').astype(int)
        
        # Category encoding (frequency-based)
        category_freq = df['category'].value_counts(normalize=True)
        df['category_freq'] = df['category'].map(category_freq)
        
        # Description length
        df['desc_length'] = df['description'].str.len()
        
        # Rolling features (if enough data)
        if len(df) >= 7:
            df = df.sort_values('date')
            df['rolling_mean_7d'] = df.groupby('type')['amount'].transform(
                lambda x: x.rolling(window=7, min_periods=1).mean()
            )
            df['rolling_std_7d'] = df.groupby('type')['amount'].transform(
                lambda x: x.rolling(window=7, min_periods=1).std()
            )
        else:
            df['rolling_mean_7d'] = df['amount']
            df['rolling_std_7d'] = 0
        
        # Select features for clustering
        feature_cols = [
            'amount', 'amount_log', 'day_of_week', 'day_of_month', 
            'month', 'is_weekend', 'is_expense', 'category_freq',
            'desc_length', 'rolling_mean_7d', 'rolling_std_7d'
        ]
        
        X = df[feature_cols].fillna(0).values
        
        return df, X
    
    def find_optimal_clusters(self, X: np.ndarray, max_k: int = 10) -> Dict[str, Any]:
        """Find optimal number of clusters using elbow method and silhouette score"""
        inertias = []
        silhouette_scores = []
        calinski_scores = []
        
        k_range = range(2, min(max_k + 1, len(X) // 2))
        
        for k in k_range:
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(X)
            
            inertias.append(kmeans.inertia_)
            silhouette_scores.append(silhouette_score(X, labels))
            calinski_scores.append(calinski_harabasz_score(X, labels))
        
        # Find elbow point (maximum second derivative)
        if len(inertias) >= 3:
            second_derivative = np.diff(np.diff(inertias))
            optimal_k = int(np.argmax(second_derivative)) + 2
        else:
            optimal_k = 3
        
        # Also consider best silhouette score
        best_silhouette_k = int(np.argmax(silhouette_scores)) + 2
        
        return {
            'optimal_k_elbow': optimal_k,
            'optimal_k_silhouette': best_silhouette_k,
            'recommended_k': best_silhouette_k,  # Prefer silhouette
            'inertias': inertias,
            'silhouette_scores': silhouette_scores,
            'calinski_scores': calinski_scores,
            'k_range': list(k_range)
        }
    
    def cluster_kmeans(self, X: np.ndarray, n_clusters: Optional[int] = None) -> Dict[str, Any]:
        """K-Means clustering"""
        if n_clusters is None:
            n_clusters = self.n_clusters
        
        model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = model.fit_predict(X)
        
        silhouette = silhouette_score(X, labels) if len(set(labels)) > 1 else 0
        calinski = calinski_harabasz_score(X, labels) if len(set(labels)) > 1 else 0
        
        self.model = model
        self.labels = labels
        self.cluster_centers = model.cluster_centers_
        
        return {
            'method': 'kmeans',
            'labels': labels.tolist(),
            'n_clusters': n_clusters,
            'silhouette_score': float(silhouette),
            'calinski_score': float(calinski),
            'inertia': float(model.inertia_)
        }
    
    def cluster_dbscan(self, X: np.ndarray, eps: float = 0.5, min_samples: int = 5) -> Dict[str, Any]:
        """DBSCAN clustering"""
        model = DBSCAN(eps=eps, min_samples=min_samples)
        labels = model.fit_predict(X)
        
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_noise = list(labels).count(-1)
        
        if n_clusters > 1:
            # Calculate metrics only for non-noise points
            mask = labels != -1
            if mask.sum() > 0:
                silhouette = silhouette_score(X[mask], labels[mask])
                calinski = calinski_harabasz_score(X[mask], labels[mask])
            else:
                silhouette = 0
                calinski = 0
        else:
            silhouette = 0
            calinski = 0
        
        self.model = model
        self.labels = labels
        
        return {
            'method': 'dbscan',
            'labels': labels.tolist(),
            'n_clusters': n_clusters,
            'n_noise': n_noise,
            'silhouette_score': float(silhouette),
            'calinski_score': float(calinski)
        }
    
    def cluster_hierarchical(self, X: np.ndarray, n_clusters: Optional[int] = None) -> Dict[str, Any]:
        """Hierarchical Agglomerative clustering"""
        if n_clusters is None:
            n_clusters = self.n_clusters
        
        model = AgglomerativeClustering(n_clusters=n_clusters)
        labels = model.fit_predict(X)
        
        silhouette = silhouette_score(X, labels) if len(set(labels)) > 1 else 0
        calinski = calinski_harabasz_score(X, labels) if len(set(labels)) > 1 else 0
        
        self.model = model
        self.labels = labels
        
        return {
            'method': 'hierarchical',
            'labels': labels.tolist(),
            'n_clusters': n_clusters,
            'silhouette_score': float(silhouette),
            'calinski_score': float(calinski)
        }
    
    def reduce_dimensions(self, X: np.ndarray, method: str = 'pca', 
                         n_components: int = 2) -> np.ndarray:
        """Dimensionality reduction for visualization"""
        if method == 'pca':
            pca = PCA(n_components=n_components)
            X_reduced = pca.fit_transform(X)
            self.pca = pca
            return X_reduced
        
        elif method == 'tsne' and len(X) >= 4:
            tsne = TSNE(n_components=n_components, random_state=42)
            X_reduced = tsne.fit_transform(X)
            return X_reduced
        
        elif method == 'umap' and UMAP_AVAILABLE and len(X) >= 4:
            reducer = umap.UMAP(n_components=n_components, random_state=42)
            X_reduced = reducer.fit_transform(X)
            return X_reduced
        
        else:
            # Fallback to first 2 features
            return X[:, :n_components] if X.shape[1] >= n_components else X
    
    def analyze_clusters(self, df: pd.DataFrame, labels: np.ndarray) -> Dict[str, Any]:
        """Analyze and describe each cluster"""
        df = df.copy()
        df['cluster'] = labels
        
        cluster_analysis = {}
        
        for cluster_id in sorted(set(labels)):
            if cluster_id == -1:  # Skip noise in DBSCAN
                continue
            
            cluster_data = df[df['cluster'] == cluster_id]
            
            cluster_analysis[int(cluster_id)] = {
                'size': len(cluster_data),
                'percentage': len(cluster_data) / len(df) * 100,
                'avg_amount': float(cluster_data['amount'].mean()),
                'median_amount': float(cluster_data['amount'].median()),
                'total_amount': float(cluster_data['amount'].sum()),
                'most_common_category': cluster_data['category'].mode()[0] if not cluster_data['category'].empty else 'unknown',
                'income_expense_ratio': {
                    'income': int((cluster_data['type'] == 'income').sum()),
                    'expense': int((cluster_data['type'] == 'expense').sum())
                },
                'avg_day_of_week': float(cluster_data['day_of_week'].mean()),
                'weekend_percentage': float((cluster_data['is_weekend'] == 1).sum() / len(cluster_data) * 100)
            }
        
        return cluster_analysis
    
    def cluster(self, incomes_qs, expenses_qs, auto_select: bool = True) -> Dict[str, Any]:
        """
        Main clustering method
        
        Args:
            incomes_qs: Django queryset of incomes
            expenses_qs: Django queryset of expenses
            auto_select: Automatically select optimal number of clusters
        
        Returns:
            Clustering results with analysis
        """
        # Extract features
        df, X = self.extract_features(incomes_qs, expenses_qs)
        
        if len(X) < 4:
            return {
                'success': False,
                'error': 'Insufficient data for clustering (need at least 4 transactions)'
            }
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Find optimal clusters if auto_select
        if auto_select and self.method == 'kmeans':
            optimal_info = self.find_optimal_clusters(X_scaled)
            self.n_clusters = optimal_info['recommended_k']
        
        # Perform clustering
        if self.method == 'kmeans':
            result = self.cluster_kmeans(X_scaled)
        elif self.method == 'dbscan':
            result = self.cluster_dbscan(X_scaled)
        elif self.method == 'hierarchical':
            result = self.cluster_hierarchical(X_scaled)
        else:
            # Auto: try kmeans first
            result = self.cluster_kmeans(X_scaled)
        
        if not result:
            return {
                'success': False,
                'error': 'Clustering failed'
            }
        
        # Analyze clusters
        cluster_analysis = self.analyze_clusters(df, np.array(result['labels']))
        
        # Dimensionality reduction for visualization
        X_2d_pca = self.reduce_dimensions(X_scaled, method='pca', n_components=2)
        
        # Add cluster labels to original data
        df['cluster'] = result['labels']
        df['x_2d'] = X_2d_pca[:, 0]
        df['y_2d'] = X_2d_pca[:, 1] if X_2d_pca.shape[1] > 1 else 0
        
        # Prepare visualization data
        viz_data = []
        for _, row in df.iterrows():
            viz_data.append({
                'id': int(row['id']),
                'x': float(row['x_2d']),
                'y': float(row['y_2d']),
                'cluster': int(row['cluster']),
                'amount': float(row['amount']),
                'type': row['type'],
                'category': row['category'],
                'date': row['date'].strftime('%Y-%m-%d')
            })
        
        return {
            'success': True,
            'method': result['method'],
            'n_clusters': result['n_clusters'],
            'metrics': {
                'silhouette_score': result.get('silhouette_score', 0),
                'calinski_score': result.get('calinski_score', 0)
            },
            'cluster_analysis': cluster_analysis,
            'visualization_data': viz_data,
            'total_transactions': len(df)
        }
    
    def predict_cluster(self, transaction_features: Dict[str, float]) -> int:
        """Predict cluster for a new transaction"""
        if self.model is None or not hasattr(self.model, 'predict'):
            return -1
        
        # Prepare features in same order as training
        features = [
            transaction_features.get('amount', 0),
            transaction_features.get('amount_log', 0),
            transaction_features.get('day_of_week', 0),
            transaction_features.get('day_of_month', 1),
            transaction_features.get('month', 1),
            transaction_features.get('is_weekend', 0),
            transaction_features.get('is_expense', 0),
            transaction_features.get('category_freq', 0.1),
            transaction_features.get('desc_length', 0),
            transaction_features.get('rolling_mean_7d', 0),
            transaction_features.get('rolling_std_7d', 0)
        ]
        
        X = np.array([features])
        X_scaled = self.scaler.transform(X)
        
        cluster = self.model.predict(X_scaled)[0]
        return int(cluster)
