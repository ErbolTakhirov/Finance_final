# ML Архитектура SB Finance - Детальное описание

## 1. Общая архитектура системы

```
┌─────────────────────────────────────────────────────────────────┐
│                      Django Web Application                       │
│                         (sb_finance)                             │
└─────────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
    ┌────▼────┐         ┌─────▼─────┐       ┌─────▼─────┐
    │ Views   │         │   Models   │       │    URLs   │
    │(views.py)│       │ (models.py) │       │(urls.py) │
    └────┬────┘         └─────┬─────┘       └───────────┘
         │                    │
         └────────────────────┼────────────────────┐
                              │                    │
                         ┌────▼────────────────┐  │
                         │                     │  │
                    ┌────▼──────┐        ┌────▼──┐
                    │    ML     │        │ Utils │
                    │  System   │        │       │
                    └───────────┘        └───────┘
                          │                  │
            ┌─────────────┼──────────────────┼──────────────┐
            │             │                  │              │
        ┌───▼───┐    ┌────▼────┐       ┌────▼───┐    ┌─────▼────┐
        │Predict│    │Forecast │       │Analytics│   │Anonymizer│
        │(ML)   │    │(sklearn)│       │(stats)  │   │          │
        └───────┘    └─────────┘       └─────────┘   └──────────┘
            │             │                  │              │
    ┌───────┴──────┐  ┌──┴──────┐      ┌────┴─────┐   ┌────┴──────┐
    │Recommend     │  │Document │      │Anomaly   │   │Encrypt    │
    │(rules)       │  │Generator│      │Detection │   │(AES-256)  │
    └──────────────┘  └─────────┘      └──────────┘   └───────────┘
            │             │                  │              │
            └─────────────┼──────────────────┼──────────────┘
                          │                  │
                    ┌─────▼──────────────────▼────┐
                    │   External Services         │
                    ├─────────────────────────────┤
                    │ • OpenRouter LLM API        │
                    │ • Ollama (local LLM)        │
                    │ • Hugging Face Models       │
                    │ • Scikit-learn/NumPy        │
                    └─────────────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Data Storage      │
                    ├────────────────────┤
                    │ • SQLite/PostgreSQL│
                    │ • Media files      │
                    │ • ML Models        │
                    │ • Encrypted data   │
                    └────────────────────┘
```

---

## 2. Детальная архитектура ML модулей

### 2.1 Модуль Автокатегоризации (predictor.py)

```
┌─────────────────────────────────────────────────────────┐
│        ExpenseAutoCategorizer                           │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  __init__()                                      │  │
│  │  • Проверяет наличие media/ml/expense_         │  │
│  │    classifier.joblib                            │  │
│  │  • Загружает модель joblib.load()              │  │
│  │  • Если ошибка → self.model = None             │  │
│  └──────────────────────────────────────────────────┘  │
│                         │                               │
│                         ▼                               │
│  ┌──────────────────────────────────────────────────┐  │
│  │  predict_category(text: str)                     │  │
│  │                                                  │  │
│  │  input: "Оплата аренды офиса за март"          │  │
│  └──────────────────────────────────────────────────┘  │
│                    │         │                          │
│        ┌───────────┘         └──────────────┐          │
│        │                                    │          │
│   ┌────▼─────────────────┐    ┌────────────▼───────┐  │
│   │ ML PATH              │    │ FALLBACK PATH      │  │
│   │ (if model exists)    │    │ (if no model)      │  │
│   │                      │    │                    │  │
│   │ 1. self.model != None│    │ 1. text.lower()   │  │
│   │ 2. try:             │    │ 2. Check keywords: │  │
│   │    pred = model.     │    │                    │  │
│   │    predict([text])   │    │ Keyword mapping:  │  │
│   │ 3. return str(pred)  │    │ • rent: аренда    │  │
│   │ 4. except → pass     │    │ • tax: налог      │  │
│   │                      │    │ • salary: зарплат │  │
│   │                      │    │ • marketing: реклам
│   │                      │    │ • purchase: закуп │  │
│   │                      │    │ • other: default  │  │
│   └────┬─────────────────┘    └────────────┬───────┘  │
│        │                                    │          │
│        └─────────────────┬──────────────────┘          │
│                          │                             │
│                    ┌─────▼──────────┐                 │
│                    │   output:      │                 │
│                    │  'rent'        │                 │
│                    │  'tax'         │                 │
│                    │  'salary'      │                 │
│                    │  'marketing'   │                 │
│                    │  'purchase'    │                 │
│                    │  'other'       │                 │
│                    │  or None       │                 │
│                    └────────────────┘                 │
└─────────────────────────────────────────────────────────┘
```

**Жизненный цикл:**

```
1. Инициализация (один раз):
   ExpenseAutoCategorizer() → __init__() → joblib.load() или None

2. Предсказание (многократно):
   predict_category("text") → ML или Fallback → категория

3. Интеграция:
   for row in csv:
       category = categorizer.predict_category(row['description'])
       Expense(category=category).save()
```

---

### 2.2 Модуль Обучения Модели (train_classifier.py)

```
┌──────────────────────────────────────────────────────┐
│  train_classifier.py                                 │
│                                                      │
│  ┌────────────────────────────────────────────────┐ │
│  │  load_demo_data()                              │ │
│  │  ───────────────────────────────────────────  │ │
│  │  [                                             │ │
│  │    ('Оплата аренды офиса за март', 'rent'),  │ │
│  │    ('Налоговый платёж НДС', 'tax'),          │ │
│  │    ('Зарплата сотрудникам', 'salary'),       │ │
│  │    ('Запуск рекламной кампании', 'marketing'),│ │
│  │    ('Закупка сырья и материалов', 'purchase'),│ │
│  │    ... (всего 12 примеров)                    │ │
│  │  ]                                             │ │
│  └──────────────┬─────────────────────────────────┘ │
│                 │                                    │
│        ┌────────▼────────┐                          │
│        │ pd.DataFrame    │                          │
│        │ [text, category]│                          │
│        └────────┬────────┘                          │
│                 │                                    │
│        ┌────────▼────────┐                          │
│        │ train_test_split│                          │
│        │ 80/20           │                          │
│        │                 │                          │
│        │ X_train, X_test │                          │
│        │ y_train, y_test │                          │
│        └────────┬────────┘                          │
│                 │                                    │
│  ┌──────────────▼──────────────────────────────────┐ │
│  │  sklearn Pipeline:                               │ │
│  │  ┌────────────────────────────────────────────┐ │ │
│  │  │ Stage 1: TfidfVectorizer                   │ │ │
│  │  │ • ngram_range=(1, 2) - унграммы + биграммы│ │ │
│  │  │ • min_df=1 - минимальное вхождение        │ │ │
│  │  │ • Выход: TF-IDF матрица (n_samples, n_feats)│ │ │
│  │  └────────────────────────────────────────────┘ │ │
│  │  ┌────────────────────────────────────────────┐ │ │
│  │  │ Stage 2: LogisticRegression                │ │ │
│  │  │ • max_iter=1000 - максимум итераций       │ │ │
│  │  │ • Вход: TF-IDF вектора                     │ │ │
│  │  │ • Выход: предсказанный класс (category)   │ │ │
│  │  └────────────────────────────────────────────┘ │ │
│  └──────────────┬──────────────────────────────────┘ │
│                 │                                    │
│        ┌────────▼────────┐                          │
│        │ pipe.fit()      │                          │
│        │ X_train, y_train│                          │
│        └────────┬────────┘                          │
│                 │                                    │
│        ┌────────▼────────────┐                      │
│        │ pipe.predict(X_test)│                      │
│        │ y_pred              │                      │
│        └────────┬────────────┘                      │
│                 │                                    │
│        ┌────────▼────────────┐                      │
│        │ classification_     │                      │
│        │ report()            │                      │
│        │ (печать метрик)     │                      │
│        └────────┬────────────┘                      │
│                 │                                    │
│        ┌────────▼──────────────┐                    │
│        │ joblib.dump(pipe)     │                    │
│        │ → media/ml/expense_   │                    │
│        │   classifier.joblib   │                    │
│        └───────────────────────┘                    │
└──────────────────────────────────────────────────────┘
```

**Команда для обучения:**

```bash
$ python core/ml/train_classifier.py

# Выход:
#               precision    recall  f1-score   support
#          marketing       1.00      1.00      1.00         1
#              other       0.00      0.00      0.00         0
#           purchase       1.00      1.00      1.00         1
#              rent       1.00      1.00      1.00         1
#             salary       1.00      1.00      1.00         1
#               tax       1.00      1.00      1.00         1
#
#       accuracy                           1.00         4
#      macro avg       0.83      0.83      0.83         4
#   weighted avg       1.00      1.00      1.00         4
#
# Model saved to media/ml/expense_classifier.joblib
```

---

### 2.3 Модуль Прогнозирования (forecast.py)

```
┌────────────────────────────────────────────────────────┐
│  forecast_next_month_profit()                          │
│                                                        │
│  Input:                                                │
│  • incomes_qs: QuerySet(Income)                        │
│  • expenses_qs: QuerySet(Expense)                      │
└────────┬───────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│  Aggregation by Month                                  │
│                                                        │
│  by_month = {}                                         │
│  for income in incomes:                                │
│    key = income.date.replace(day=1)                    │
│    by_month[key] += income.amount                      │
│                                                        │
│  for expense in expenses:                              │
│    key = expense.date.replace(day=1)                   │
│    by_month[key] -= expense.amount                     │
│                                                        │
│  Result:                                               │
│  {                                                     │
│    2024-01-01: 65000.0,   # доходы - расходы         │
│    2024-02-01: 88000.0,                               │
│    2024-03-01: 95000.0                                │
│  }                                                     │
└────────┬───────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│  Check Data Validity                                   │
│                                                        │
│  if not by_month:                                      │
│    return None                                         │
│                                                        │
│  months = [2024-01, 2024-02, 2024-03]                 │
│  profits = [65000, 88000, 95000]                       │
│                                                        │
│  if len(profits) == 1:                                 │
│    return profits[0]  # Вернуть за один месяц          │
└────────┬───────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│  Linear Regression                                     │
│                                                        │
│  X = [[0],        (индекс месяца)                      │
│       [1],                                             │
│       [2]]                                             │
│                                                        │
│  y = [65000,      (прибыль)                            │
│       88000,                                           │
│       95000]                                           │
│                                                        │
│  model = LinearRegression()                            │
│  model.fit(X, y)                                       │
│                                                        │
│  Fitted: y = 14500*x + 57500                           │
│  (примерно)                                            │
└────────┬───────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│  Forecast Next Month                                   │
│                                                        │
│  next_idx = len(months) = 3                            │
│  pred = model.predict([[3]])                           │
│  → 44500*3 + 57500 = 101500                            │
└────────┬───────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│  Output: float (прибыль на следующий месяц)            │
│  → 101500.0                                            │
└────────────────────────────────────────────────────────┘
```

**Пример использования:**

```python
from core.ml.forecast import forecast_next_month_profit
from core.models import Income, Expense

user = User.objects.get(username='john')
incomes = Income.objects.filter(user=user)
expenses = Expense.objects.filter(user=user)

forecast = forecast_next_month_profit(incomes, expenses)
print(f"Forecast: {forecast:,.2f} RUB")  # → 101500.00 RUB
```

---

### 2.4 Модуль Рекомендаций (recommender.py)

```
┌──────────────────────────────────────────────────┐
│  build_recommendations()                         │
│                                                  │
│  Input:                                          │
│  • incomes_qs                                    │
│  • expenses_qs                                   │
└──────────────┬───────────────────────────────────┘
               │
               ▼
        ┌──────────────────┐
        │ Rule 1: Check    │
        │ high expenses    │
        │ per category     │
        └──────────┬───────┘
                   │
     ┌─────────────┴─────────────┐
     │                           │
┌────▼────────────────────┐  ┌──▼──────────────────┐
│ total_expense = 100000  │  │ by_category = {     │
│                         │  │  'marketing': 42000,│
│ Calculate percent:      │  │  'salary': 35000,  │
│ marketing: 42%          │  │  'rent': 15000,    │
│ salary: 35%             │  │  'other': 8000     │
│ rent: 15%               │  │ }                   │
│                         │  │                     │
│ If > 40%:               │  │ if 42000/100000 >   │
│ → "Слишком высокие      │  │    0.4:             │
│   расходы по маркетингу"│  │   → Add to recs    │
└─────────────────────────┘  └─────────────────────┘
     │
     ▼
┌──────────────────────────────────────────────────┐
│ Rule 2: Check income decrease                    │
│                                                  │
│ if len(income_values) >= 6:                      │
│   recent_3m = sum(last_3_months) / 3             │
│   prev_3m = sum(months_4to6) / 3                 │
│                                                  │
│   if recent_3m < prev_3m * 0.9:  # 10% drop    │
│     → "Замечено снижение доходов..."            │
└──────────────┬───────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────┐
│ Default Rule: Stability check                    │
│                                                  │
│ if not recs:  # No issues found                  │
│   → "Финансовые показатели стабильны..."        │
└──────────────┬───────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────┐
│ Output: List[str] - recommendations              │
│                                                  │
│ [                                                │
│   "Слишком высокие расходы по категории          │
│    'marketing'. Рассмотрите оптимизацию затрат.",│
│   "Замечено снижение доходов. Усильте продажи...",
│   "Финансовые показатели стабильны..."           │
│ ]                                                │
└──────────────────────────────────────────────────┘
```

---

### 2.5 Модуль Генерации Документов (document_generator.py)

```
┌──────────────────────────────────────────────────┐
│  generate_document_text(doc_type, params)        │
│                                                  │
│  Input:                                          │
│  • doc_type: 'invoice' | 'act' | 'contract'     │
│  • params: {client, total, details}              │
└──────────────┬───────────────────────────────────┘
               │
               ▼
        ┌──────────────────┐
        │ _lazy_load()     │ (Ленивая загрузка)
        │                  │
        │ if _HF_AVAILABLE │ (Hugging Face)
        │   load model     │
        │   load tokenizer │
        └──────────┬───────┘
                   │
     ┌─────────────┴──────────────┐
     │                            │
┌────▼──────────────────┐  ┌─────▼──────────────┐
│ ML PATH                │  │ FALLBACK PATH      │
│ (Hugging Face GPT-2)   │  │ (Template)         │
│                        │  │                    │
│ 1. Build prompt:       │  │ Simple template    │
│  "Сгенерируй invoice   │  │ with params        │
│   на русском языке...  │  │                    │
│   Клиент: ООО Компа    │  │ def _fallback_     │
│   ния, Сумма: 50000..."│  │ template(type):    │
│                        │  │   if type ==       │
│ 2. Encode:             │  │      'invoice':    │
│    input_ids =         │  │   return "Счет..." │
│    tokenizer.encode()  │  │                    │
│                        │  │                    │
│ 3. Generate:           │  │                    │
│    output = model.     │  │                    │
│    generate(           │  │                    │
│      input_ids,        │  │                    │
│      max_new_tokens=80,│  │                    │
│      do_sample=True,   │  │                    │
│      top_k=50,         │  │                    │
│      top_p=0.95        │  │                    │
│    )                   │  │                    │
│                        │  │                    │
│ 4. Decode:             │  │                    │
│    text = tokenizer.   │  │                    │
│    decode(output[0])   │  │                    │
└────┬───────────────────┘  └────┬────────────┘
     │                           │
     └────────────┬──────────────┘
                  │
                  ▼
        ┌─────────────────────┐
        │ Output: str         │
        │ (Generated document │
        │  text)              │
        └─────────────────────┘
```

**Пример генерации:**

```python
from core.ml.document_generator import generate_document_text

# Параметры
params = {
    'client': 'ООО Рога и Копыта',
    'total': '50000.00',
    'details': 'Консультационные услуги'
}

# Генерация
invoice = generate_document_text('invoice', params)

# Результат (примерный):
# "Счет на оплату
#  Плательщик: ООО Рога и Копыта
#  Сумма: 50000.00
#  Назначение: Консультационные услуги
#  
#  Данный счет выставлен в соответствии с договором..."
```

---

## 3. Модуль Аналитики (analytics.py)

```
┌──────────────────────────────────────────────────────┐
│  analyze_finances(user)                              │
└──────────────┬───────────────────────────────────────┘
               │
     ┌─────────┼──────────┐
     │         │          │
┌────▼───┐ ┌───▼────┐ ┌──▼─────┐
│Income  │ │Expense │ │Event   │
│QuerySet│ │QuerySet│ │QuerySet│
└────┬───┘ └───┬────┘ └───┬────┘
     │         │          │
     └─────────┼──────────┘
               │
               ▼
        ┌──────────────────────┐
        │aggregate_by_month()  │ ← Main aggregation
        │                      │
        │ Result:              │
        │ {                    │
        │   "2024-01": {       │
        │     income_total,    │
        │     expense_total,   │
        │     balance,         │
        │     top_categories,  │
        │     change_pct, ...  │
        │   },                 │
        │   "2024-02": {...},  │
        │   ...                │
        │ }                    │
        └──────────┬───────────┘
                   │
     ┌─────────────┼──────────────┐
     │             │              │
┌────▼──────┐ ┌───▼────┐ ┌──────▼────┐
│Anomalies  │ │Trends  │ │Health     │
│Detection  │ │Analysis│ │Score      │
│           │ │        │ │           │
│_detect_   │ │_analyze│ │assess_    │
│expense_   │ │_trends │ │financial_ │
│anomalies()│ │()      │ │health()   │
└────┬──────┘ └───┬────┘ └──────┬────┘
     │            │             │
     │ Z-score    │ Growth/     │ Savings
     │ detection  │ Decline/    │ ratio
     │            │ Stable      │ Volatility
     │            │             │ Anomalies
     │            │             │
     └─────────────┼─────────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │ Recommendations      │
        │ build_recommendations│
        └──────────┬───────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │ Format Output        │
        │                      │
        │ • Markdown table     │
        │ • Text summary       │
        │ • JSON structure     │
        └──────────┬───────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │ Return to API        │
        │                      │
        │ {                    │
        │  monthly_summary,    │
        │  anomalies,          │
        │  trends,             │
        │  recommendations,    │
        │  health_score,       │
        │  ...                 │
        │ }                    │
        └──────────────────────┘
```

---

## 4. Data Flow Diagram - полный цикл анализа

```
┌─────────────────┐
│ User uploads    │
│ CSV/Excel file  │
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│ file_ingest.py      │
│ • Parse file        │
│ • Validate data     │
└────────┬────────────┘
         │
         ▼
┌──────────────────────────────────────┐
│ For each transaction:                │
│ • ExpenseAutoCategorizer.predict()   │
│ • Map to UploadedFile                │
│ • Check for duplicates (optional)    │
└────────┬─────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────┐
│ Save to Database:                    │
│ • Expense/Income records             │
│ • UploadedFile metadata              │
│ • Update UserProfile.financial_memory│
└────────┬─────────────────────────────┘
         │
         ▼
┌─────────────────────┐
│ User requests       │
│ /api/ai-insights/   │
└────────┬────────────┘
         │
         ▼
┌──────────────────────────────────────┐
│ analyze_finances(user)               │
│                                      │
│ 1. aggregate_by_month()              │
│ 2. _detect_expense_anomalies()       │
│ 3. _analyze_trends()                 │
│ 4. assess_financial_health()         │
│ 5. build_recommendations()           │
└────────┬─────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Format Results:                      │
│ • Markdown table                    │
│ • Text summary                      │
│ • JSON structure                    │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Optional: LLM Enhancement            │
│ get_llm_response(                    │
│   prompt=analysis,                   │
│   anonymize=True,                    │
│   system_prompt="Financial analyst"  │
│ )                                    │
│                                      │
│ Routes to:                           │
│ • OpenRouter API (cloud)             │
│ • Ollama endpoint (local)            │
└────────┬────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────┐
│ Return to Client:                    │
│ {                                    │
│   "monthly_summary": "markdown",     │
│   "anomalies": [...],                │
│   "trends": {...},                   │
│   "recommendations": [...],          │
│   "health_score": 75,                │
│   "llm_insights": "Optional text"    │
│ }                                    │
└──────────────────────────────────────┘
```

---

## 5. State Diagram - модели и состояния

```
┌────────────────────────┐
│  Income/Expense        │
│  Lifecycle             │
└────────────────────────┘
        │
        ├─ Created: user=null, encrypted=false
        │
        ├─ [File Import]
        │   ├─ source_file = UploadedFile
        │   ├─ category = Predicted
        │   ├─ is_encrypted = false (по умолчанию)
        │
        ├─ [User Edit]
        │   ├─ category = Manual
        │   ├─ description = Updated
        │   ├─ encrypted_data = if enabled
        │   └─ is_encrypted = true
        │
        └─ [Deleted]
            ├─ on_delete=CASCADE → UploadedFile
            └─ tags.clear()


┌────────────────────────┐
│  UploadedFile          │
│  Lifecycle             │
└────────────────────────┘
        │
        ├─ Uploaded: processed=false
        │   ├─ file_type = 'csv', 'xlsx', 'pdf', 'docx'
        │   ├─ file_size = bytes
        │   ├─ metadata = {}
        │
        ├─ [Processing]
        │   ├─ Extract transactions
        │   ├─ Auto-categorize
        │   ├─ Detect duplicates
        │   └─ Create Income/Expense records
        │
        └─ Processed: processed=true
            ├─ metadata.transaction_count
            ├─ metadata.duplicates_found
            └─ incomes.all() / expenses.all()


┌────────────────────────┐
│  UserProfile           │
│  Settings              │
└────────────────────────┘
        │
        ├─ encryption_enabled: bool
        │   └─ Controls encrypted_data in records
        │
        ├─ local_mode_only: bool
        │   └─ Routes LLM requests to Ollama only
        │
        ├─ auto_clear_file_on_import: bool
        │   └─ On re-import: delete old transactions
        │
        ├─ auto_remove_duplicates: bool
        │   └─ During import: skip duplicates
        │
        ├─ financial_memory: JSON
        │   ├─ Last analysis results
        │   ├─ Key metrics
        │   └─ Context for LLM
        │
        └─ success_cases: JSON[]
            └─ History of successful recommendations
```

---

## 6. Database Schema для ML компонентов

```sql
-- Income/Expense: основные таблицы
CREATE TABLE core_income (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES auth_user(id),
    amount FLOAT NOT NULL,
    date DATE NOT NULL,
    category VARCHAR(50) NOT NULL,
    description TEXT,
    source_file_id INTEGER REFERENCES core_uploadedfile(id),
    encrypted_data TEXT,
    is_encrypted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_income_user_date ON core_income(user_id, date);
CREATE INDEX idx_income_category ON core_income(category);

-- Аналогично для expenses...

-- UserProfile: метаданные пользователя
CREATE TABLE core_userprofile (
    id INTEGER PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES auth_user(id),
    encryption_enabled BOOLEAN DEFAULT TRUE,
    local_mode_only BOOLEAN DEFAULT FALSE,
    financial_memory JSON DEFAULT '{}',
    success_cases JSON DEFAULT '[]',
    auto_clear_file_on_import BOOLEAN DEFAULT FALSE,
    auto_remove_duplicates BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- UploadedFile: информация о загруженных файлах
CREATE TABLE core_uploadedfile (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES auth_user(id),
    file VARCHAR(255) NOT NULL,
    original_name VARCHAR(255),
    file_type VARCHAR(50),  -- 'csv', 'xlsx', 'pdf', 'docx'
    file_size INTEGER,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT FALSE,
    metadata JSON DEFAULT '{}'
);

CREATE INDEX idx_uploadedfile_user_date ON core_uploadedfile(user_id, uploaded_at);
```

---

## 7. Configuration & Settings

```python
# settings.py

# LLM Configuration
LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'openrouter')  # 'openrouter' | 'ollama'
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'gpt-3.5-turbo')
OLLAMA_API_URL = os.getenv('OLLAMA_API_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama2')

# Media & Models
MEDIA_ROOT = BASE_DIR / 'media'
ML_MODELS_PATH = MEDIA_ROOT / 'ml'

# Anonymization settings
ANONYMIZATION_PATTERNS = {
    'account': r'\b\d{16,20}\b',
    'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    'phone': r'\b\+?7\d{10}\b',
}

# Analytics thresholds
ANOMALY_Z_SCORE_THRESHOLD = 2.0
EXPENSE_RATIO_THRESHOLD = 0.4  # 40%
INCOME_DROP_THRESHOLD = 0.1  # 10%
```

---

## 8. Integration Points with Django Views

```python
# core/views.py

class AIInsightsView(APIView):
    """GET /api/ai-insights/"""
    def get(self, request):
        analysis = analyze_finances(request.user)
        return Response(analysis)

class ForecastView(APIView):
    """GET /api/forecast/"""
    def get(self, request):
        forecast = forecast_next_month_profit(
            Income.objects.filter(user=request.user),
            Expense.objects.filter(user=request.user)
        )
        return Response({'forecast': forecast})

class DocumentGenerateView(APIView):
    """POST /api/documents/generate/"""
    def post(self, request):
        doc_type = request.data.get('type')
        params = request.data.get('params')
        text = generate_document_text(doc_type, params)
        
        document = Document.objects.create(
            user=request.user,
            doc_type=doc_type,
            params=params,
            generated_text=text
        )
        return Response({'id': document.id, 'text': text})

class FilesUploadView(APIView):
    """POST /api/files/upload/"""
    def post(self, request):
        file = request.FILES['file']
        uploaded_file = ingest_file(request.user, file)
        return Response({'file_id': uploaded_file.id})
```

---

## 9. Performance & Scalability Considerations

```
┌──────────────────────────────────────────────────┐
│  Performance Optimization                        │
├──────────────────────────────────────────────────┤
│                                                  │
│ 1. Model Caching:                                │
│    • ExpenseAutoCategorizer loads model once     │
│    • Hugging Face models use lazy loading        │
│    • Joblib model cached in memory               │
│                                                  │
│ 2. Database Indexing:                            │
│    CREATE INDEX idx_income_user_date             │
│    • Fast filtering by user + date               │
│    • Optimization for aggregation queries        │
│                                                  │
│ 3. Batch Processing:                             │
│    • Process multiple transactions together      │
│    • Vectorized operations in numpy              │
│    • Pandas groupby for aggregation              │
│                                                  │
│ 4. Caching Results:                              │
│    • Store analysis results in JSONField         │
│    • Cache LLM responses                         │
│    • Invalidate on new transaction               │
│                                                  │
│ 5. Async Tasks (for long-running):               │
│    • Model training (Celery)                     │
│    • Large file processing                       │
│    • LLM generation                              │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

## 10. Error Handling & Fallbacks

```
┌─────────────────────────────────────────────────┐
│  Error Handling Strategy                        │
├─────────────────────────────────────────────────┤
│                                                 │
│ ExpenseAutoCategorizer:                         │
│   ├─ Model load failure → use keyword fallback  │
│   ├─ Prediction error → return 'other'          │
│   └─ Empty text → return None                   │
│                                                 │
│ Forecast:                                       │
│   ├─ Insufficient data → return None            │
│   ├─ Math error → return last value             │
│   └─ Empty QuerySet → return None               │
│                                                 │
│ Analytics:                                      │
│   ├─ No transactions → empty result             │
│   ├─ Division by zero → handled                 │
│   └─ Missing data → skip metric                 │
│                                                 │
│ Document Generator:                             │
│   ├─ HF model unavailable → template fallback   │
│   ├─ Generation error → template output         │
│   └─ Tokenizer error → return param summary     │
│                                                 │
│ LLM Integration:                                │
│   ├─ OpenRouter down → try Ollama               │
│   ├─ Ollama down → return local rules           │
│   ├─ Rate limit → queue request                 │
│   └─ Timeout → return cached result             │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

**Версия документации:** 1.0  
**Дата обновления:** 2024-12-16  
**Ветка Git:** docs-ml-full-description-52x
