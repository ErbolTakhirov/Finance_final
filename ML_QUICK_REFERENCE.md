# ML System - Быстрый справочник

## 📌 TL;DR - Кратко о всём

ML система SB Finance состоит из **5 основных компонентов**:

| Модуль | Файл | Что делает | Вход | Выход |
|--------|------|-----------|------|-------|
| **Predictor** | `predictor.py` | Автокатегоризация расходов | Описание расхода | Категория |
| **Forecast** | `forecast.py` | Прогноз прибыли на месяц | Истор. доходы/расходы | Число (прибыль) |
| **Recommender** | `recommender.py` | Финансовые рекомендации | Доходы/расходы | Список советов |
| **DocGenerator** | `document_generator.py` | Генерация документов | Параметры (тип, сумма) | Текст документа |
| **Analytics** | `analytics.py` | Анализ и аномалии | Все транзакции | Таблица, тренды, оценка |

---

## 🚀 Быстрый старт

### 1. Импорт и использование

```python
# Автокатегоризация
from core.ml.predictor import ExpenseAutoCategorizer
cat = ExpenseAutoCategorizer()
category = cat.predict_category("Оплата аренды")  # → 'rent'

# Прогноз
from core.ml.forecast import forecast_next_month_profit
forecast = forecast_next_month_profit(incomes_qs, expenses_qs)  # → 65000.0

# Рекомендации
from core.ml.recommender import build_recommendations
recs = build_recommendations(incomes_qs, expenses_qs)  # → ['rec1', 'rec2', ...]

# Документы
from core.ml.document_generator import generate_document_text
text = generate_document_text('invoice', params)  # → 'Счет на оплату...'

# Аналитика
from core.utils.analytics import analyze_finances
analysis = analyze_finances(user)  # → {'monthly_summary': '...', ...}
```

---

## 📊 Компоненты в деталях

### Predictor (ExpenseAutoCategorizer)

```
Используется при: Импорте CSV, создании расхода без категории
Модель: sklearn Pipeline (TF-IDF + LogisticRegression)
Файл модели: media/ml/expense_classifier.joblib
Fallback: Ключевые слова на русском

Категории: rent, tax, salary, marketing, purchase, other
```

**Обучение:**
```bash
python core/ml/train_classifier.py
```

### Forecast (LinearRegression)

```
Используется при: Запросе прогноза прибыли
Метод: Линейная регрессия по месячным данным
Требует: Минимум 2 месяца данных
Выход: float или None
```

### Recommender (Rule-based)

```
Используется при: Запросе рекомендаций
Правило 1: Если расход по категории > 40% → "Высокие расходы"
Правило 2: Если доходы упали > 10% → "Снижение доходов"
Fallback: "Стабильно"
```

### DocGenerator (Hugging Face)

```
Используется при: Генерации счетов, актов, договоров
Модель: sshleifer/tiny-gpt2 (или шаблон fallback)
Типы: invoice, act, contract
Требует: Параметры (client, total, details)
```

### Analytics (Statistical)

```
Используется при: Запросе полного анализа финансов
Включает:
  - Агрегацию по месяцам
  - Обнаружение аномалий (Z-score)
  - Анализ трендов
  - Оценку здоровья (0-100)
  - Markdown таблицу
```

---

## 🔗 API Endpoints

| Метод | URL | Компонент | Описание |
|-------|-----|-----------|---------|
| GET | `/api/ai-insights/` | Analytics | Полный анализ финансов |
| GET | `/api/forecast/` | Forecast | Прогноз прибыли |
| POST | `/api/documents/generate/` | DocGenerator | Создать документ |
| POST | `/api/files/upload/` | Predictor + Analytics | Импортировать файл |
| POST | `/api/chat/` | LLM | Chat с AI |

---

## 📁 Структура файлов

```
core/
├── ml/
│   ├── predictor.py           ← Автокатегоризация
│   ├── forecast.py            ← Прогноз
│   ├── recommender.py         ← Рекомендации
│   ├── document_generator.py  ← Генерация документов
│   └── train_classifier.py    ← Обучение модели
├── utils/
│   ├── analytics.py           ← Аналитика
│   ├── anonymizer.py          ← Анонимизация для LLM
│   ├── encryption.py          ← Шифрование
│   ├── file_ingest.py         ← Импорт файлов
│   └── export.py              ← Экспорт данных
├── llm.py                     ← Интеграция LLM
├── models.py                  ← Django модели
├── views.py                   ← API endpoints
└── urls.py                    ← URL маршруты
```

---

## 💾 Модели Django

```python
# Основные модели
Income           # Доходы (amount, date, category, description, source_file)
Expense          # Расходы (аналогично Income)
UploadedFile     # Загруженные файлы (file, file_type, processed, metadata)
UserProfile      # Профиль пользователя (encryption_enabled, financial_memory, ...)
Document         # Сгенерированные документы (doc_type, params, generated_text)

# Индексы
Index(['user', 'date'])          # Быстрая фильтрация по дате
Index(['source_file', 'date'])   # Поиск по источнику файла
```

---

## 🔧 Конфигурация

### settings.py

```python
# LLM
LLM_PROVIDER = 'openrouter'  # или 'ollama'
OPENROUTER_API_KEY = 'your-key'
OPENROUTER_MODEL = 'gpt-3.5-turbo'
OLLAMA_API_URL = 'http://localhost:11434'

# ML модели
MEDIA_ROOT = 'media/'  # media/ml/expense_classifier.joblib

# Анонимизация
ANONYMIZATION_PATTERNS = {
    'account': r'\b\d{16,20}\b',
    'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
}
```

### .env

```
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-xxx
OPENROUTER_MODEL=gpt-3.5-turbo
LOCAL_MODE_ONLY=false
ANONYMIZE_DATA=true
```

---

## 📈 Примеры вывода

### Analytics (analyze_finances)

```json
{
  "monthly_summary": "| Месяц | Доходы | ... |",
  "anomalies": [
    {
      "amount": 125000.0,
      "category": "marketing",
      "date": "2024-01-15",
      "z_score": 2.45,
      "threshold": 75000.0
    }
  ],
  "trends": {
    "income_trend": "growth",
    "income_trend_pct": 8.5,
    "expense_trend": "stable"
  },
  "recommendations": [
    "Слишком высокие расходы по категории 'marketing'...",
    "Финансовые показатели стабильны..."
  ],
  "health_score": 75
}
```

### Forecast

```
60000.0  (прибыль на следующий месяц)
```

### Recommender

```
[
  "Слишком высокие расходы по категории 'marketing'. Рассмотрите оптимизацию затрат.",
  "Замечено снижение доходов. Усильте продажи/маркетинг и проработайте воронку."
]
```

---

## ⚠️ Типичные ошибки и решения

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `model=None` | Модель не обучена | `python core/ml/train_classifier.py` |
| `forecast=None` | < 2 месяцев данных | Загрузить больше истории |
| `LLM timeout` | API недоступен | Включить `local_mode_only=True` |
| `Низкая точность катег.` | Недостаточно примеров | Добавить примеры в `train_classifier.py` |
| `Ошибка шифрования` | Неверный пароль | Проверить `encryption_enabled` в профиле |

---

## 🎯 Common Tasks

### Задача: Автокатегоризировать все расходы

```python
from core.ml.predictor import ExpenseAutoCategorizer
from core.models import Expense

categorizer = ExpenseAutoCategorizer()
for expense in Expense.objects.filter(user=user, category__in=['', None]):
    expense.category = categorizer.predict_category(expense.description)
    expense.save()
```

### Задача: Получить анализ финансов

```python
from core.utils.analytics import analyze_finances

analysis = analyze_finances(user)
print(analysis['monthly_summary'])     # Markdown таблица
print(analysis['recommendations'])     # Список советов
print(analysis['health_score'])        # Оценка 0-100
```

### Задача: Прогнозировать прибыль

```python
from core.ml.forecast import forecast_next_month_profit
from core.models import Income, Expense

forecast = forecast_next_month_profit(
    Income.objects.filter(user=user),
    Expense.objects.filter(user=user)
)
print(f"Прогноз: {forecast:,.2f} RUB")
```

### Задача: Сгенерировать документ

```python
from core.ml.document_generator import generate_document_text
from core.models import Document

text = generate_document_text('invoice', {
    'client': 'ООО Компания',
    'total': '50000',
    'details': 'Услуги'
})

Document.objects.create(
    user=user,
    doc_type='invoice',
    params={'client': 'ООО Компания', 'total': '50000', 'details': 'Услуги'},
    generated_text=text
)
```

---

## 📚 Дополнительные документы

- `ML_SYSTEM_FULL_DESCRIPTION.md` - Полное описание системы
- `ML_ARCHITECTURE_DETAILED.md` - Архитектурные диаграммы
- `ML_USAGE_EXAMPLES.md` - Примеры кода и сценарии

---

## 🔗 Полезные ссылки

- [sklearn Documentation](https://scikit-learn.org)
- [Hugging Face Transformers](https://huggingface.co/transformers)
- [Django Documentation](https://docs.djangoproject.com)
- [OpenRouter API](https://openrouter.ai)
- [Ollama](https://ollama.ai)

---

## ✅ Чек-лист для разработчика

- [ ] Модель обучена: `python core/ml/train_classifier.py`
- [ ] `.env` файл заполнен (LLM_PROVIDER, API keys)
- [ ] Тесты проходят: `python manage.py test`
- [ ] Миграции применены: `python manage.py migrate`
- [ ] Есть тестовые данные в БД
- [ ] API endpoints протестированы
- [ ] Документация актуальна

---

## 🎓 Рекомендации для улучшения

1. **Predictor**: Использовать RuBERT вместо TF-IDF (BERT точнее, но медленнее)
2. **Forecast**: Добавить ARIMA/Prophet для учёта сезонности
3. **Analytics**: Добавить machine-learning для обнаружения аномалий (Isolation Forest)
4. **DocGenerator**: Использовать GPT-4 вместо tiny-gpt2 через LLM API
5. **LLM**: Сохранять контекст пользователя для более точных ответов

---

**Версия:** 1.0  
**Дата:** 2024-12-16  
**Ветка:** docs-ml-full-description-52x  
**Автор:** ML Documentation  
