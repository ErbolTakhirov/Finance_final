"""
Model Explainability Module
- SHAP values for model interpretation
- Feature importance analysis
- Individual prediction explanations
"""

import warnings
from typing import Dict, List, Optional, Any

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False

from sklearn.inspection import permutation_importance


class ModelExplainer:
    """
    Explains model predictions using SHAP values and other interpretability methods
    """
    
    def __init__(self, model, feature_names: List[str]):
        """
        Args:
            model: Trained scikit-learn compatible model
            feature_names: List of feature names
        """
        self.model = model
        self.feature_names = feature_names
        self.explainer = None
        self.shap_values = None
        
    def initialize_shap_explainer(self, X_background: np.ndarray, model_type: str = 'tree'):
        """
        Initialize SHAP explainer
        
        Args:
            X_background: Background dataset for SHAP (training data sample)
            model_type: 'tree', 'linear', 'kernel', 'deep'
        """
        if not SHAP_AVAILABLE:
            return False
        
        try:
            if model_type == 'tree':
                self.explainer = shap.TreeExplainer(self.model)
            elif model_type == 'linear':
                self.explainer = shap.LinearExplainer(self.model, X_background)
            elif model_type == 'kernel':
                self.explainer = shap.KernelExplainer(self.model.predict, X_background)
            else:
                # Auto-detect
                if hasattr(self.model, 'tree_'):
                    self.explainer = shap.TreeExplainer(self.model)
                else:
                    self.explainer = shap.KernelExplainer(self.model.predict, 
                                                         shap.sample(X_background, min(100, len(X_background))))
            return True
        except Exception as e:
            print(f"SHAP initialization error: {e}")
            return False
    
    def explain_prediction(self, X: np.ndarray, instance_idx: int = 0) -> Dict[str, Any]:
        """
        Explain a single prediction using SHAP values
        
        Args:
            X: Feature matrix
            instance_idx: Index of instance to explain
        
        Returns:
            Explanation with feature contributions
        """
        if not SHAP_AVAILABLE or self.explainer is None:
            return self._fallback_explain(X, instance_idx)
        
        try:
            # Calculate SHAP values for this instance
            shap_values = self.explainer.shap_values(X[instance_idx:instance_idx+1])
            
            # Handle multi-class case
            if isinstance(shap_values, list):
                # For multi-class, use values for predicted class
                pred_class = self.model.predict(X[instance_idx:instance_idx+1])[0]
                shap_values_instance = shap_values[pred_class][0]
            else:
                shap_values_instance = shap_values[0]
            
            # Get base value (expected value)
            base_value = self.explainer.expected_value
            if isinstance(base_value, np.ndarray) or isinstance(base_value, list):
                base_value = base_value[0]
            
            # Sort features by absolute SHAP value
            feature_contributions = []
            for i, (feature, shap_val) in enumerate(zip(self.feature_names, shap_values_instance)):
                feature_contributions.append({
                    'feature': feature,
                    'value': float(X[instance_idx, i]),
                    'shap_value': float(shap_val),
                    'abs_shap_value': float(abs(shap_val))
                })
            
            feature_contributions.sort(key=lambda x: x['abs_shap_value'], reverse=True)
            
            return {
                'success': True,
                'method': 'shap',
                'base_value': float(base_value),
                'prediction': float(self.model.predict(X[instance_idx:instance_idx+1])[0]),
                'feature_contributions': feature_contributions,
                'top_features': feature_contributions[:5]
            }
        
        except Exception as e:
            print(f"SHAP explanation error: {e}")
            return self._fallback_explain(X, instance_idx)
    
    def _fallback_explain(self, X: np.ndarray, instance_idx: int) -> Dict[str, Any]:
        """Fallback explanation using feature importance"""
        if not hasattr(self.model, 'feature_importances_'):
            return {
                'success': False,
                'error': 'Model does not support feature importance'
            }
        
        importances = self.model.feature_importances_
        feature_contributions = []
        
        for i, (feature, importance) in enumerate(zip(self.feature_names, importances)):
            feature_contributions.append({
                'feature': feature,
                'value': float(X[instance_idx, i]),
                'importance': float(importance),
                'contribution': float(X[instance_idx, i] * importance)
            })
        
        feature_contributions.sort(key=lambda x: abs(x['contribution']), reverse=True)
        
        return {
            'success': True,
            'method': 'feature_importance',
            'prediction': float(self.model.predict(X[instance_idx:instance_idx+1])[0]),
            'feature_contributions': feature_contributions,
            'top_features': feature_contributions[:5]
        }
    
    def get_global_feature_importance(self, X: np.ndarray) -> Dict[str, Any]:
        """
        Get global feature importance across all predictions
        
        Args:
            X: Feature matrix (full dataset or sample)
        
        Returns:
            Global feature importance ranking
        """
        results = {}
        
        # Method 1: Model's built-in feature importance
        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
            results['model_importance'] = [
                {
                    'feature': feature,
                    'importance': float(imp),
                    'rank': rank + 1
                }
                for rank, (feature, imp) in enumerate(
                    sorted(zip(self.feature_names, importances), 
                          key=lambda x: x[1], reverse=True)
                )
            ]
        
        # Method 2: Permutation importance
        try:
            y = self.model.predict(X)
            perm_importance = permutation_importance(
                self.model, X, y, n_repeats=10, random_state=42
            )
            
            results['permutation_importance'] = [
                {
                    'feature': feature,
                    'importance': float(imp),
                    'std': float(std),
                    'rank': rank + 1
                }
                for rank, (feature, imp, std) in enumerate(
                    sorted(zip(self.feature_names, 
                             perm_importance.importances_mean,
                             perm_importance.importances_std), 
                          key=lambda x: x[1], reverse=True)
                )
            ]
        except Exception as e:
            print(f"Permutation importance error: {e}")
        
        # Method 3: SHAP global importance
        if SHAP_AVAILABLE and self.explainer is not None:
            try:
                # Calculate SHAP values for sample
                sample_size = min(100, len(X))
                X_sample = X[:sample_size]
                shap_values = self.explainer.shap_values(X_sample)
                
                # Handle multi-class
                if isinstance(shap_values, list):
                    shap_values = shap_values[0]
                
                # Mean absolute SHAP value for each feature
                mean_abs_shap = np.abs(shap_values).mean(axis=0)
                
                results['shap_importance'] = [
                    {
                        'feature': feature,
                        'importance': float(imp),
                        'rank': rank + 1
                    }
                    for rank, (feature, imp) in enumerate(
                        sorted(zip(self.feature_names, mean_abs_shap), 
                              key=lambda x: x[1], reverse=True)
                    )
                ]
            except Exception as e:
                print(f"SHAP global importance error: {e}")
        
        return {
            'success': True,
            'methods': list(results.keys()),
            'importance_rankings': results
        }
    
    def explain_dataset(self, X: np.ndarray, max_samples: int = 100) -> Dict[str, Any]:
        """
        Generate explanations for entire dataset (or sample)
        
        Args:
            X: Feature matrix
            max_samples: Maximum number of samples to explain
        
        Returns:
            Summary statistics of explanations
        """
        if not SHAP_AVAILABLE or self.explainer is None:
            return {
                'success': False,
                'error': 'SHAP not available or explainer not initialized'
            }
        
        try:
            # Sample if dataset is large
            if len(X) > max_samples:
                indices = np.random.choice(len(X), max_samples, replace=False)
                X_sample = X[indices]
            else:
                X_sample = X
            
            # Calculate SHAP values
            shap_values = self.explainer.shap_values(X_sample)
            
            # Handle multi-class
            if isinstance(shap_values, list):
                shap_values = shap_values[0]
            
            # Calculate statistics
            mean_abs_shap = np.abs(shap_values).mean(axis=0)
            std_shap = np.abs(shap_values).std(axis=0)
            
            feature_stats = []
            for i, feature in enumerate(self.feature_names):
                feature_stats.append({
                    'feature': feature,
                    'mean_abs_shap': float(mean_abs_shap[i]),
                    'std_shap': float(std_shap[i]),
                    'min_shap': float(shap_values[:, i].min()),
                    'max_shap': float(shap_values[:, i].max()),
                })
            
            # Sort by mean absolute SHAP value
            feature_stats.sort(key=lambda x: x['mean_abs_shap'], reverse=True)
            
            return {
                'success': True,
                'n_samples_explained': len(X_sample),
                'feature_statistics': feature_stats,
                'top_features': feature_stats[:10]
            }
        
        except Exception as e:
            print(f"Dataset explanation error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_explanation_text(self, explanation: Dict[str, Any]) -> str:
        """
        Generate human-readable explanation text
        
        Args:
            explanation: Result from explain_prediction
        
        Returns:
            Human-readable explanation
        """
        if not explanation.get('success'):
            return "Не удалось сгенерировать объяснение."
        
        pred = explanation.get('prediction', 0)
        top_features = explanation.get('top_features', [])
        
        text = f"Прогноз модели: {pred:.2f}\n\n"
        text += "Наиболее важные факторы:\n"
        
        for i, feat_contrib in enumerate(top_features, 1):
            feature = feat_contrib['feature']
            value = feat_contrib.get('value', 0)
            
            if explanation['method'] == 'shap':
                shap_val = feat_contrib.get('shap_value', 0)
                impact = "увеличивает" if shap_val > 0 else "уменьшает"
                text += f"{i}. {feature} = {value:.2f} {impact} прогноз на {abs(shap_val):.3f}\n"
            else:
                importance = feat_contrib.get('importance', 0)
                text += f"{i}. {feature} = {value:.2f} (важность: {importance:.3f})\n"
        
        return text


def create_explainer_for_model(model, X_train: np.ndarray, 
                                feature_names: List[str],
                                model_type: str = 'tree') -> ModelExplainer:
    """
    Factory function to create and initialize explainer
    
    Args:
        model: Trained model
        X_train: Training data for background
        feature_names: List of feature names
        model_type: Type of model for SHAP
    
    Returns:
        Initialized ModelExplainer
    """
    explainer = ModelExplainer(model, feature_names)
    
    # Initialize SHAP if available
    if SHAP_AVAILABLE:
        # Use sample of training data as background
        background_size = min(100, len(X_train))
        X_background = X_train[:background_size]
        explainer.initialize_shap_explainer(X_background, model_type)
    
    return explainer
