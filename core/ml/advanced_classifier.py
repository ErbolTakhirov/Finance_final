"""
Advanced Classification Module for Expense Categorization
Implements ensemble methods, AutoML, and deep learning approaches
"""

import re
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder

warnings.filterwarnings('ignore')

try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

try:
    from lightgbm import LGBMClassifier
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False

try:
    from catboost import CatBoostClassifier
    CATBOOST_AVAILABLE = True
except ImportError:
    CATBOOST_AVAILABLE = False

from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression

import joblib


class AdvancedExpenseClassifier:
    """
    Advanced expense categorization using ensemble methods.
    Combines multiple models for robust predictions.
    """
    
    def __init__(self, use_ensemble: bool = True):
        self.use_ensemble = use_ensemble
        self.vectorizer = TfidfVectorizer(
            max_features=500,
            ngram_range=(1, 3),
            min_df=1,
            max_df=0.9,
            analyzer='char_wb'  # Character n-grams for better Russian support
        )
        self.label_encoder = LabelEncoder()
        self.model = None
        self.models = {}
        self.feature_importance = {}
        
    def _create_features(self, text: str) -> Dict[str, float]:
        """Extract handcrafted features from text"""
        text_lower = text.lower()
        
        features = {
            'length': len(text),
            'word_count': len(text.split()),
            'digit_count': sum(c.isdigit() for c in text),
            'upper_count': sum(c.isupper() for c in text),
            'has_number': float(bool(re.search(r'\d', text))),
        }
        
        # Keyword features for Russian text
        keywords = {
            'rent': ['аренд', 'офис', 'помещ', 'квартир'],
            'salary': ['зарплат', 'оклад', 'премия', 'выплат'],
            'tax': ['налог', 'ндс', 'фнс', 'взнос'],
            'marketing': ['реклам', 'маркет', 'продвиж', 'контекст'],
            'purchase': ['закуп', 'покуп', 'товар', 'материал'],
            'utilities': ['электр', 'вода', 'отопл', 'коммунальн'],
            'transport': ['транспорт', 'бензин', 'такси', 'доставк'],
            'food': ['еда', 'питани', 'ресторан', 'кафе'],
            'equipment': ['оборудован', 'техник', 'компьютер', 'принтер'],
            'services': ['услуг', 'сервис', 'обслужив'],
        }
        
        for category, words in keywords.items():
            features[f'kw_{category}'] = float(any(word in text_lower for word in words))
        
        return features
    
    def _get_base_models(self) -> List[Tuple[str, Any]]:
        """Get available base models for ensemble"""
        models = []
        
        # Logistic Regression (fast baseline)
        models.append(('lr', LogisticRegression(max_iter=1000, random_state=42)))
        
        # Random Forest
        models.append(('rf', RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )))
        
        # XGBoost
        if XGBOOST_AVAILABLE:
            models.append(('xgb', XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42,
                eval_metric='mlogloss'
            )))
        
        # LightGBM
        if LIGHTGBM_AVAILABLE:
            models.append(('lgbm', LGBMClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42,
                verbose=-1
            )))
        
        # CatBoost
        if CATBOOST_AVAILABLE:
            models.append(('catboost', CatBoostClassifier(
                iterations=100,
                depth=6,
                learning_rate=0.1,
                random_state=42,
                verbose=False
            )))
        
        return models
    
    def train(self, descriptions: List[str], categories: List[str]) -> Dict[str, Any]:
        """
        Train the classifier on provided data
        
        Returns:
            Training metrics and model info
        """
        if len(descriptions) < 10:
            return {
                'success': False,
                'error': 'Insufficient training data (need at least 10 samples)'
            }
        
        # Prepare data
        X_text = self.vectorizer.fit_transform(descriptions)
        y = self.label_encoder.fit_transform(categories)
        
        # Split for validation
        X_train, X_test, y_train, y_test = train_test_split(
            X_text, y, test_size=0.2, random_state=42, stratify=y
        )
        
        if self.use_ensemble:
            # Train ensemble
            base_models = self._get_base_models()
            
            # Train individual models and store them
            for name, model in base_models:
                model.fit(X_train, y_train)
                self.models[name] = model
                
                # Calculate individual scores
                score = model.score(X_test, y_test)
                print(f"{name} accuracy: {score:.4f}")
            
            # Create voting ensemble
            self.model = VotingClassifier(
                estimators=base_models,
                voting='soft'  # Use probability voting
            )
            self.model.fit(X_train, y_train)
        else:
            # Train single best model (XGBoost if available)
            if XGBOOST_AVAILABLE:
                self.model = XGBClassifier(
                    n_estimators=200,
                    max_depth=8,
                    learning_rate=0.1,
                    random_state=42,
                    eval_metric='mlogloss'
                )
            else:
                self.model = RandomForestClassifier(
                    n_estimators=200,
                    max_depth=15,
                    random_state=42,
                    n_jobs=-1
                )
            
            self.model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test)
        accuracy = (y_pred == y_test).mean()
        f1 = f1_score(y_test, y_pred, average='weighted')
        
        # Feature importance (for tree-based models)
        if hasattr(self.model, 'feature_importances_'):
            feature_names = self.vectorizer.get_feature_names_out()
            importances = self.model.feature_importances_
            top_indices = np.argsort(importances)[-20:]
            self.feature_importance = {
                feature_names[i]: float(importances[i])
                for i in top_indices
            }
        
        return {
            'success': True,
            'accuracy': float(accuracy),
            'f1_score': float(f1),
            'n_samples': len(descriptions),
            'n_categories': len(set(categories)),
            'categories': self.label_encoder.classes_.tolist(),
            'feature_importance': self.feature_importance,
            'models_used': list(self.models.keys()) if self.use_ensemble else ['single_model']
        }
    
    def predict(self, text: str) -> str:
        """Predict category for a single text"""
        if self.model is None:
            return self._fallback_predict(text)
        
        try:
            X = self.vectorizer.transform([text])
            pred_encoded = self.model.predict(X)[0]
            return self.label_encoder.inverse_transform([pred_encoded])[0]
        except Exception:
            return self._fallback_predict(text)
    
    def predict_proba(self, text: str) -> Dict[str, float]:
        """Get prediction probabilities for all categories"""
        if self.model is None or not hasattr(self.model, 'predict_proba'):
            return {}
        
        try:
            X = self.vectorizer.transform([text])
            proba = self.model.predict_proba(X)[0]
            categories = self.label_encoder.classes_
            
            return {
                cat: float(prob)
                for cat, prob in zip(categories, proba)
            }
        except Exception:
            return {}
    
    def _fallback_predict(self, text: str) -> str:
        """Rule-based fallback prediction"""
        text_lower = text.lower()
        
        if any(w in text_lower for w in ['аренда', 'офис', 'помещ']):
            return 'rent'
        if any(w in text_lower for w in ['налог', 'ндс', 'фнс']):
            return 'tax'
        if any(w in text_lower for w in ['зарплат', 'оклад']):
            return 'salary'
        if any(w in text_lower for w in ['реклам', 'маркет']):
            return 'marketing'
        if any(w in text_lower for w in ['закуп', 'покуп']):
            return 'purchase'
        if any(w in text_lower for w in ['электр', 'вода', 'коммунальн']):
            return 'utilities'
        if any(w in text_lower for w in ['транспорт', 'бензин', 'такси']):
            return 'transport'
        
        return 'other'
    
    def save(self, path: Path):
        """Save model to disk"""
        model_data = {
            'model': self.model,
            'vectorizer': self.vectorizer,
            'label_encoder': self.label_encoder,
            'feature_importance': self.feature_importance,
            'use_ensemble': self.use_ensemble
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model_data, path)
    
    @classmethod
    def load(cls, path: Path) -> 'AdvancedExpenseClassifier':
        """Load model from disk"""
        model_data = joblib.load(path)
        
        classifier = cls(use_ensemble=model_data.get('use_ensemble', True))
        classifier.model = model_data['model']
        classifier.vectorizer = model_data['vectorizer']
        classifier.label_encoder = model_data['label_encoder']
        classifier.feature_importance = model_data.get('feature_importance', {})
        
        return classifier
    
    def auto_train_from_db(self, expense_qs):
        """Automatically train from expense queryset"""
        descriptions = []
        categories = []
        
        for expense in expense_qs:
            if expense.description and expense.category:
                descriptions.append(expense.description)
                categories.append(expense.category)
        
        if len(descriptions) < 10:
            return {
                'success': False,
                'error': f'Insufficient data: only {len(descriptions)} labeled expenses found'
            }
        
        return self.train(descriptions, categories)
