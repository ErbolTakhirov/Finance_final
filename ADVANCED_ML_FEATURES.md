# 🚀 Advanced ML Features - Comprehensive Guide

## Overview

Этот проект теперь включает продвинутые Data Science и Machine Learning возможности, использующие state-of-the-art алгоритмы и методы.

## 🎯 Core ML Capabilities

### 1. Advanced Forecasting (Продвинутое прогнозирование)

**Реализованные модели:**
- **Prophet** - Facebook's time series forecasting с учетом сезонности, праздников и трендов
- **ARIMA/SARIMAX** - Статистические модели авто-регрессии с интегрированным скользящим средним
- **LSTM** - Глубокое обучение с рекуррентными нейронными сетями
- **Ensemble** - Комбинация всех моделей для максимальной точности

**Особенности:**
- Автоматический выбор лучшей модели на основе R² score
- Доверительные интервалы (95%)
- Месячные и дневные прогнозы
- Метрики качества: MAE, RMSE, R²

**API Endpoint:**
```http
POST /api/ml/forecast/advanced/
Content-Type: application/json

{
  "method": "auto",  // or "prophet", "arima", "lstm", "ensemble"
  "periods": 30,     // days to forecast
  "monthly": false   // set true for monthly forecast
}
```

**Минимальные требования:** 10+ транзакций

---

### 2. Anomaly Detection (Обнаружение аномалий)

**Реализованные алгоритмы:**
- **Isolation Forest** - Изоляция аномалий через случайные деревья
- **One-Class SVM** - Support Vector Machine для новизны
- **Local Outlier Factor (LOF)** - Локальная плотность данных
- **DBSCAN** - Кластеризация с шумом
- **Autoencoder** - Нейронная сеть для обнаружения через реконструкцию
- **Statistical** - Z-score и IQR методы

**Особенности:**
- Ensemble voting (транзакция - аномалия, если большинство методов согласны)
- Confidence score для каждой аномалии
- Детальная информация об аномалиях
- Различные методы для разных типов данных

**API Endpoint:**
```http
POST /api/ml/anomaly/detect/
Content-Type: application/json

{
  "contamination": 0.1,    // expected proportion of anomalies (0.01-0.5)
  "use_ensemble": true     // use multiple algorithms
}
```

**Результат:**
```json
{
  "success": true,
  "n_anomalies": 15,
  "anomaly_percentage": 5.2,
  "anomalies": [
    {
      "id": 123,
      "type": "expense",
      "date": "2024-01-15",
      "amount": 50000.0,
      "category": "marketing",
      "confidence": 0.87,
      "detection_count": 5,
      "total_methods": 6
    }
  ],
  "methods_used": ["isolation_forest", "one_class_svm", "lof", "dbscan", "autoencoder", "statistical"]
}
```

---

### 3. Smart Clustering (Умная кластеризация)

**Реализованные методы:**
- **K-Means** - Центроиды с автоматическим определением оптимального K
- **DBSCAN** - Density-based clustering с обнаружением шума
- **Hierarchical (Agglomerative)** - Иерархическая кластеризация

**Особенности:**
- Автоматический выбор оптимального количества кластеров (elbow method + silhouette score)
- Dimensionality reduction для визуализации (PCA, t-SNE, UMAP)
- Детальный анализ каждого кластера
- Метрики качества: Silhouette Score, Calinski-Harabasz

**API Endpoint:**
```http
POST /api/ml/clustering/
Content-Type: application/json

{
  "method": "auto",        // or "kmeans", "dbscan", "hierarchical"
  "n_clusters": 5,         // for kmeans/hierarchical
  "auto_select": true      // automatically find optimal k
}
```

**Анализ кластеров:**
```json
{
  "cluster_analysis": {
    "0": {
      "size": 50,
      "percentage": 20.5,
      "avg_amount": 1500.0,
      "median_amount": 1200.0,
      "most_common_category": "food",
      "income_expense_ratio": {
        "income": 10,
        "expense": 40
      }
    }
  }
}
```

---

### 4. Advanced Classification (Продвинутая классификация)

**Реализованные модели:**
- **XGBoost** - Gradient boosting с экстремальной производительностью
- **LightGBM** - Microsoft's gradient boosting
- **CatBoost** - Yandex's gradient boosting
- **Random Forest** - Ансамбль решающих деревьев
- **Logistic Regression** - Базовая линия

**Особенности:**
- Ensemble voting для максимальной точности
- TF-IDF векторизация с n-gramами для русского текста
- Feature importance analysis
- Вероятности для каждой категории
- Автоматическое обучение на пользовательских данных

**API Endpoints:**

Обучение модели:
```http
POST /api/ml/classifier/train/
Content-Type: application/json

{
  "use_ensemble": true
}
```

Предсказание:
```http
POST /api/ml/classifier/predict/
Content-Type: application/json

{
  "text": "Аренда офиса в центре города"
}
```

**Результат:**
```json
{
  "success": true,
  "prediction": "rent",
  "probabilities": {
    "rent": 0.89,
    "utilities": 0.05,
    "other": 0.06
  },
  "text": "Аренда офиса в центре города"
}
```

---

### 5. Monte Carlo Simulation (Симуляция Монте-Карло)

**Возможности:**
- Симуляция будущей прибыли с учетом вероятностных распределений
- Value at Risk (VaR) и Conditional VaR
- Симуляция достижения финансовых целей
- Доверительные интервалы (5%, 25%, 75%, 95%)

**API Endpoint:**
```http
POST /api/ml/monte-carlo/
Content-Type: application/json

{
  "n_simulations": 1000,
  "days_ahead": 30
}
```

**Результат:**
```json
{
  "success": true,
  "risk_metrics": {
    "probability_of_profit": 0.78,
    "expected_profit": 15000.0,
    "value_at_risk_95": -5000.0,
    "conditional_var_95": -8000.0,
    "best_case": 45000.0,
    "worst_case": -12000.0
  },
  "daily_profit": {
    "mean": [...],
    "ci_5": [...],
    "ci_95": [...]
  }
}
```

Симуляция достижения цели:
```http
POST /api/ml/goal-simulation/
Content-Type: application/json

{
  "current_balance": 10000,
  "target": 50000,
  "monthly_income_mean": 30000,
  "monthly_income_std": 5000,
  "monthly_expense_mean": 25000,
  "monthly_expense_std": 4000,
  "max_months": 24
}
```

---

### 6. Time Series Analysis (Анализ временных рядов)

**Возможности:**
- Декомпозиция на тренд, сезонность и остатки
- Тесты на стационарность (ADF, KPSS)
- Автокорреляционный анализ
- Обнаружение структурных изменений

**API Endpoint:**
```http
GET /api/ml/time-series/decompose/?period=7
```

**Результат:**
```json
{
  "success": true,
  "dates": ["2024-01-01", ...],
  "original": [100, 150, ...],
  "trend": [120, 125, ...],
  "seasonal": [10, -5, ...],
  "residual": [-30, 30, ...],
  "period": 7
}
```

---

### 7. Interactive Visualizations (Интерактивные визуализации)

**Реализованные графики:**
- **Sankey Diagram** - Денежный поток от доходов к расходам
- **Sunburst Chart** - Иерархическая структура расходов
- **Correlation Heatmap** - Корреляция между категориями
- **Advanced Dashboard** - Комплексная панель с множеством графиков
- **Forecast Charts** - Прогнозы с доверительными интервалами
- **Anomaly Scatter** - Визуализация аномалий
- **Treemap** - Структура расходов

**API Endpoints:**
```http
GET /api/ml/viz/sankey/
GET /api/ml/viz/sunburst/
GET /api/ml/viz/correlation/
GET /api/ml/viz/dashboard/
```

Все визуализации возвращают Plotly JSON, который можно отрендерить на фронтенде:
```json
{
  "success": true,
  "figure_json": "{...plotly figure...}"
}
```

---

### 8. Cohort Analysis (Когортный анализ)

**Возможности:**
- Анализ транзакций по месячным когортам
- Month-over-month рост
- Retention patterns
- Spending patterns по когортам

**API Endpoint:**
```http
GET /api/ml/cohort-analysis/
```

---

## 🎨 ML Showcase Page

Интерактивная страница демонстрации всех ML возможностей:

**URL:** `http://localhost:8000/ml-showcase/`

Страница позволяет:
- Протестировать все ML модели в один клик
- Увидеть результаты в реальном времени
- Интерактивные Plotly графики
- Метрики качества моделей
- Красивый modern UI

---

## 📊 Model Explainability (Объяснимость моделей)

**SHAP Values:**
- Feature importance для каждого предсказания
- Global feature importance
- Локальные объяснения (почему модель предсказала X)
- Visualizations

**LIME:**
- Local interpretable model-agnostic explanations
- Понятные объяснения для пользователей

---

## 🔧 Technical Stack

### Machine Learning
- **scikit-learn** - Базовые ML алгоритмы
- **XGBoost, LightGBM, CatBoost** - Gradient boosting
- **Prophet** - Time series forecasting
- **statsmodels** - Статистические модели (ARIMA)
- **PyTorch** - Deep learning (LSTM, Autoencoders)
- **TensorFlow** - Альтернативный DL фреймворк

### Data Science
- **pandas, numpy** - Обработка данных
- **scipy** - Научные вычисления
- **statsmodels** - Статистический анализ

### Explainability
- **SHAP** - Model interpretation
- **LIME** - Local explanations

### Visualization
- **Plotly** - Интерактивные графики
- **Seaborn** - Статистические визуализации
- **Matplotlib** - Базовые графики

---

## 💡 Best Practices

### 1. Data Requirements

Для качественных результатов рекомендуется:
- **Forecasting**: минимум 30+ транзакций, лучше 100+
- **Anomaly Detection**: минимум 20+ транзакций
- **Clustering**: минимум 10+ транзакций
- **Classification**: минимум 50+ размеченных транзакций для обучения

### 2. Model Selection

- **Для прогнозирования**: используйте `method: "auto"` - система выберет лучшую модель
- **Для аномалий**: используйте ensemble для максимальной точности
- **Для кластеризации**: `auto_select: true` для автоматического определения оптимального K

### 3. Interpretation

Всегда проверяйте:
- Метрики качества (R², MAE, RMSE)
- Confidence scores
- Feature importance
- Доверительные интервалы

---

## 🚀 Quick Start

1. **Установите зависимости:**
```bash
pip install -r requirements.txt
```

2. **Откройте ML Showcase:**
```
http://localhost:8000/ml-showcase/
```

3. **Попробуйте все фичи:**
- Advanced Forecasting
- Anomaly Detection
- Clustering
- Monte Carlo
- Visualizations

---

## 📈 Performance

### Model Training Time
- XGBoost: ~1-2 секунды на 1000 транзакций
- LSTM: ~10-20 секунд на 1000 транзакций
- Prophet: ~3-5 секунд на 365 дней данных
- Clustering: ~1 секунда на 1000 транзакций

### Inference Time
- Predictions: <100ms
- Anomaly detection: <500ms на 1000 транзакций
- Forecasting: <1s для 30-дневного прогноза

---

## 🎓 Научная база

Все алгоритмы основаны на peer-reviewed исследованиях:

1. **Isolation Forest**: Liu et al. (2008) - "Isolation Forest"
2. **Prophet**: Taylor & Letham (2018) - "Forecasting at Scale"
3. **LSTM**: Hochreiter & Schmidhuber (1997) - "Long Short-Term Memory"
4. **XGBoost**: Chen & Guestrin (2016) - "XGBoost: A Scalable Tree Boosting System"
5. **SHAP**: Lundberg & Lee (2017) - "A Unified Approach to Interpreting Model Predictions"

---

## 🎯 Future Enhancements

Планируемые улучшения:
- [ ] Deep Learning для text classification (BERT, GPT)
- [ ] Reinforcement Learning для оптимизации расходов
- [ ] AutoML с автоматическим подбором гиперпараметров
- [ ] Real-time streaming predictions
- [ ] Multi-model ensemble with stacking
- [ ] Transfer learning from pre-trained models

---

## 📞 Support

Для вопросов по ML фичам:
- Документация: этот файл
- API docs: `/api/ml/metrics/` для списка всех возможностей
- Showcase: `/ml-showcase/` для интерактивных демо

---

**Made with ❤️ for Data Science Project Defense**
