# ML System - Примеры использования и код

## Содержание

1. [Примеры использования ML компонентов](#примеры-использования-ml-компонентов)
2. [API Endpoint примеры](#api-endpoint-примеры)
3. [Полные сценарии работы](#полные-сценарии-работы)
4. [Troubleshooting](#troubleshooting)

---

## Примеры использования ML компонентов

### 1. Автокатегоризация расходов

#### Пример 1.1: Базовое использование

```python
from core.ml.predictor import ExpenseAutoCategorizer

# Инициализация (загружает модель если существует)
categorizer = ExpenseAutoCategorizer()

# Предсказание категории
descriptions = [
    "Оплата аренды офиса за март",
    "Налоговый платёж НДС для ФНС",
    "Зарплата сотрудникам за февраль",
    "Запуск рекламной кампании в Facebook",
    "Закупка сырья и материалов",
]

for desc in descriptions:
    category = categorizer.predict_category(desc)
    print(f"{desc:40} -> {category}")

# Вывод:
# Оплата аренды офиса за март             -> rent
# Налоговый платёж НДС для ФНС            -> tax
# Зарплата сотрудникам за февраль         -> salary
# Запуск рекламной кампании в Facebook    -> marketing
# Закупка сырья и материалов              -> purchase
```

#### Пример 1.2: Интеграция с импортом CSV

```python
import csv
from core.ml.predictor import ExpenseAutoCategorizer
from core.models import Expense, UploadedFile
from django.contrib.auth.models import User

def import_expenses_with_categorization(user: User, csv_file_path: str):
    """Импортирует расходы из CSV и автоматически категоризует их"""
    
    categorizer = ExpenseAutoCategorizer()
    
    # Создаём запись о загруженном файле
    uploaded_file = UploadedFile.objects.create(
        user=user,
        file=csv_file_path,
        original_name='expenses.csv',
        file_type='csv',
        file_size=12345,
        processed=False
    )
    
    expenses_created = 0
    
    with open(csv_file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Если категория не указана или пустая
            category = row.get('category', '').strip()
            if not category:
                # Используем автокатегоризацию
                category = categorizer.predict_category(row['description'])
            
            # Создаём запись о расходе
            expense = Expense(
                user=user,
                amount=float(row['amount']),
                date=row['date'],
                category=category,
                description=row['description'],
                source_file=uploaded_file
            )
            expense.save()
            expenses_created += 1
    
    # Отмечаем файл как обработанный
    uploaded_file.processed = True
    uploaded_file.metadata = {
        'transactions_imported': expenses_created,
        'auto_categorized': True
    }
    uploaded_file.save()
    
    return expenses_created

# Использование:
user = User.objects.get(username='john_doe')
count = import_expenses_with_categorization(user, 'path/to/expenses.csv')
print(f"Импортировано расходов: {count}")
```

#### Пример 1.3: Пакетная предсказание

```python
from core.ml.predictor import ExpenseAutoCategorizer
from core.models import Expense

def auto_categorize_uncategorized_expenses(user):
    """
    Находит все расходы без категории и автоматически их категоризует
    """
    categorizer = ExpenseAutoCategorizer()
    
    # Найти расходы с пустой или None категорией
    uncategorized = Expense.objects.filter(
        user=user,
        category__in=['', None]
    )
    
    updated_count = 0
    
    for expense in uncategorized:
        new_category = categorizer.predict_category(expense.description or '')
        if new_category:
            expense.category = new_category
            expense.save()
            updated_count += 1
    
    return updated_count

# Использование:
user = User.objects.get(username='john_doe')
count = auto_categorize_uncategorized_expenses(user)
print(f"Категоризировано расходов: {count}")
```

---

### 2. Обучение модели классификации

#### Пример 2.1: Обучение с демо-данными

```bash
# Способ 1: Запуск скрипта из командной строки
python manage.py shell
>>> from core.ml.train_classifier import train
>>> train()

# Способ 2: Прямой вызов скрипта
python core/ml/train_classifier.py
```

#### Пример 2.2: Обучение с расширенным набором данных

```python
import pandas as pd
from pathlib import Path
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import joblib

def train_custom_classifier(data_list):
    """
    Обучает классификатор на пользовательском наборе данных
    
    data_list: список кортежей (text, category)
    """
    
    # Создаём DataFrame
    df = pd.DataFrame(data_list, columns=['text', 'category'])
    
    # Разделение данных
    X_train, X_test, y_train, y_test = train_test_split(
        df['text'], 
        df['category'], 
        test_size=0.2, 
        random_state=42,
        stratify=df['category']  # Сохраняет распределение классов
    )
    
    # Построение pipeline
    pipe = Pipeline([
        ('tfidf', TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=1,
            max_features=1000,
            lowercase=True,
            analyzer='char'
        )),
        ('clf', LogisticRegression(
            max_iter=2000,
            random_state=42,
            class_weight='balanced'  # Для несбалансированных классов
        ))
    ])
    
    # Обучение
    pipe.fit(X_train, y_train)
    
    # Оценка
    y_pred = pipe.predict(X_test)
    
    print("Classification Report:")
    print(classification_report(y_test, y_pred))
    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
    
    # Сохранение
    model_path = Path('media/ml/expense_classifier_custom.joblib')
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, model_path)
    
    print(f"\nМодель сохранена в {model_path}")
    return pipe

# Использование:
training_data = [
    ('Оплата офисного помещения', 'rent'),
    ('Аренда склада', 'rent'),
    ('Контраст складского помещения', 'rent'),
    ('Единый социальный налог', 'tax'),
    ('НДС к уплате', 'tax'),
    ('Налоговый платёж', 'tax'),
    ('Заработная плата', 'salary'),
    ('Премия сотрудникам', 'salary'),
    ('Оклад за месяц', 'salary'),
    ('Реклама в соцсетях', 'marketing'),
    ('Контекстная реклама', 'marketing'),
    ('Маркетинг кампания', 'marketing'),
    ('Закупка товара', 'purchase'),
    ('Приобретение материалов', 'purchase'),
    ('Покупка оборудования', 'purchase'),
]

model = train_custom_classifier(training_data)
```

#### Пример 2.3: Оценка качества модели

```python
import joblib
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

def evaluate_model(model_path, test_texts, test_labels):
    """Оценивает качество обученной модели"""
    
    model = joblib.load(model_path)
    
    # Предсказания
    predictions = model.predict(test_texts)
    
    # Метрики
    accuracy = accuracy_score(test_labels, predictions)
    precision, recall, f1, _ = precision_recall_fscore_support(
        test_labels, 
        predictions, 
        average='weighted'
    )
    
    print(f"Accuracy:  {accuracy:.3f}")
    print(f"Precision: {precision:.3f}")
    print(f"Recall:    {recall:.3f}")
    print(f"F1-Score:  {f1:.3f}")
    
    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1
    }
```

---

### 3. Прогнозирование прибыли

#### Пример 3.1: Базовое прогнозирование

```python
from core.ml.forecast import forecast_next_month_profit
from core.models import Income, Expense
from django.contrib.auth.models import User

def get_profit_forecast(user: User):
    """Получает прогноз прибыли на следующий месяц"""
    
    incomes = Income.objects.filter(user=user)
    expenses = Expense.objects.filter(user=user)
    
    forecast = forecast_next_month_profit(incomes, expenses)
    
    if forecast is None:
        return {
            'forecast': None,
            'status': 'insufficient_data',
            'message': 'Недостаточно данных для прогноза'
        }
    
    return {
        'forecast': round(forecast, 2),
        'status': 'success',
        'message': f'Прогнозируемая прибыль на следующий месяц: {forecast:,.2f} RUB'
    }

# Использование:
user = User.objects.get(username='john_doe')
result = get_profit_forecast(user)
print(result['message'])
```

#### Пример 3.2: Сравнение с историческими данными

```python
from datetime import datetime, timedelta
from core.ml.forecast import forecast_next_month_profit
from core.models import Income, Expense
import statistics

def forecast_with_comparison(user):
    """Прогнозирует прибыль и сравнивает с историческими данными"""
    
    incomes = Income.objects.filter(user=user).order_by('date')
    expenses = Expense.objects.filter(user=user).order_by('date')
    
    # Вычисляем месячную прибыль
    from collections import defaultdict
    monthly_profit = defaultdict(float)
    
    for income in incomes:
        month_key = income.date.replace(day=1)
        monthly_profit[month_key] += income.amount
    
    for expense in expenses:
        month_key = expense.date.replace(day=1)
        monthly_profit[month_key] -= expense.amount
    
    if not monthly_profit:
        return None
    
    profits = sorted(monthly_profit.values())
    
    # Получить прогноз
    forecast = forecast_next_month_profit(incomes, expenses)
    
    # Сравнение
    if len(profits) >= 3:
        avg_profit = statistics.mean(profits[-3:])
        median_profit = statistics.median(profits[-3:])
        min_profit = min(profits[-3:])
        max_profit = max(profits[-3:])
        
        return {
            'forecast': forecast,
            'average_last_3_months': avg_profit,
            'median_last_3_months': median_profit,
            'min_last_3_months': min_profit,
            'max_last_3_months': max_profit,
            'trend': 'increasing' if forecast > avg_profit else 'decreasing'
        }
    
    return {'forecast': forecast}

# Использование:
user = User.objects.get(username='john_doe')
comparison = forecast_with_comparison(user)
if comparison:
    print(f"Прогноз: {comparison['forecast']:,.2f} RUB")
    print(f"Среднее за 3 месяца: {comparison.get('average_last_3_months', 0):,.2f} RUB")
    print(f"Тренд: {comparison.get('trend', 'unknown')}")
```

---

### 4. Рекомендации

#### Пример 4.1: Получение рекомендаций

```python
from core.ml.recommender import build_recommendations
from core.models import Income, Expense
from django.contrib.auth.models import User

def get_financial_recommendations(user: User):
    """Получает финансовые рекомендации для пользователя"""
    
    incomes = Income.objects.filter(user=user)
    expenses = Expense.objects.filter(user=user)
    
    recommendations = build_recommendations(incomes, expenses)
    
    return {
        'count': len(recommendations),
        'recommendations': recommendations,
        'priority': 'high' if len(recommendations) > 1 else 'low'
    }

# Использование:
user = User.objects.get(username='john_doe')
result = get_financial_recommendations(user)
print(f"Получено рекомендаций: {result['count']}")
for i, rec in enumerate(result['recommendations'], 1):
    print(f"{i}. {rec}")
```

#### Пример 4.2: Расширенные рекомендации с LLM

```python
from core.ml.recommender import build_recommendations
from core.llm import get_llm_response
from core.models import Income, Expense, UserProfile
from django.contrib.auth.models import User

def get_enhanced_recommendations(user: User):
    """Получает рекомендации и расширяет их с помощью LLM"""
    
    incomes = Income.objects.filter(user=user)
    expenses = Expense.objects.filter(user=user)
    
    # Базовые рекомендации
    base_recs = build_recommendations(incomes, expenses)
    
    # Создаём промпт для LLM
    analysis_text = "\n".join(f"- {rec}" for rec in base_recs)
    
    prompt = f"""
    На основе следующих финансовых рекомендаций:
    
    {analysis_text}
    
    Предложи конкретные действия для улучшения финансового здоровья.
    Будь кратким и практичным.
    """
    
    # Получаем расширенные рекомендации от LLM
    try:
        llm_response = get_llm_response(
            user=user,
            prompt=prompt,
            system_prompt="Ты финансовый консультант",
            use_memory=True,
            anonymize=True
        )
    except Exception as e:
        llm_response = None
        print(f"Ошибка LLM: {e}")
    
    return {
        'base_recommendations': base_recs,
        'llm_insights': llm_response,
        'has_llm': llm_response is not None
    }

# Использование:
user = User.objects.get(username='john_doe')
result = get_enhanced_recommendations(user)
print("Базовые рекомендации:")
for rec in result['base_recommendations']:
    print(f"  • {rec}")
if result['has_llm']:
    print("\nУглубленный анализ:")
    print(result['llm_insights'])
```

---

### 5. Генерация документов

#### Пример 5.1: Генерация счета

```python
from core.ml.document_generator import generate_document_text
from core.models import Document
from django.contrib.auth.models import User

def create_invoice(user: User, client: str, amount: float, details: str):
    """Создаёт счет на оплату с автогенерацией текста"""
    
    params = {
        'client': client,
        'total': f"{amount:,.2f}",
        'details': details
    }
    
    # Генерируем текст документа
    text = generate_document_text('invoice', params)
    
    # Сохраняем в БД
    document = Document.objects.create(
        user=user,
        doc_type='invoice',
        params=params,
        generated_text=text
    )
    
    return {
        'document_id': document.id,
        'text': text,
        'params': params
    }

# Использование:
user = User.objects.get(username='john_doe')
result = create_invoice(
    user=user,
    client='ООО Компания',
    amount=50000.00,
    details='Консультационные услуги по бухгалтерии'
)
print(f"Счет #{result['document_id']}:")
print(result['text'])
```

#### Пример 5.2: Генерация акта выполненных работ

```python
from core.ml.document_generator import generate_document_text
from core.models import Document

def create_act(user, client, amount, work_description):
    """Создаёт акт выполненных работ"""
    
    params = {
        'client': client,
        'total': f"{amount:,.2f}",
        'details': work_description
    }
    
    text = generate_document_text('act', params)
    
    document = Document.objects.create(
        user=user,
        doc_type='act',
        params=params,
        generated_text=text
    )
    
    return document

# Использование:
user = User.objects.get(username='john_doe')
document = create_act(
    user=user,
    client='ООО Заказчик',
    amount=75000.00,
    work_description='Разработка веб-приложения'
)
print(f"Акт создан: #{document.id}")
```

#### Пример 5.3: Пакетная генерация документов

```python
from core.ml.document_generator import generate_document_text
from core.models import Document, Expense
from collections import defaultdict

def generate_invoices_for_expenses(user, min_amount=10000):
    """
    Генерирует счета для расходов выше определённой суммы,
    группируя их по категориям
    """
    
    large_expenses = Expense.objects.filter(
        user=user,
        amount__gte=min_amount
    )
    
    # Группируем по категориям
    by_category = defaultdict(list)
    for expense in large_expenses:
        by_category[expense.category].append(expense)
    
    documents_created = 0
    
    for category, expenses in by_category.items():
        total = sum(e.amount for e in expenses)
        details = f"{category}: {len(expenses)} транзакций"
        
        params = {
            'client': 'Клиент',
            'total': f"{total:,.2f}",
            'details': details
        }
        
        text = generate_document_text('invoice', params)
        
        Document.objects.create(
            user=user,
            doc_type='invoice',
            params=params,
            generated_text=text
        )
        
        documents_created += 1
    
    return documents_created

# Использование:
user = User.objects.get(username='john_doe')
count = generate_invoices_for_expenses(user, min_amount=25000)
print(f"Счетов создано: {count}")
```

---

## API Endpoint примеры

### API 1: Аналитика и рекомендации

```python
# Файл: core/views.py

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from core.utils.analytics import analyze_finances

@api_view(['GET'])
def ai_insights(request):
    """
    GET /api/ai-insights/
    
    Возвращает полный анализ финансов пользователя:
    - Месячные данные (таблица)
    - Обнаруженные аномалии
    - Анализ трендов
    - Финансовые рекомендации
    - Оценка здоровья
    """
    try:
        analysis = analyze_finances(request.user)
        return Response(analysis, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# Использование:
# curl -H "Authorization: Bearer TOKEN" \
#      http://localhost:8000/api/ai-insights/
```

**Пример ответа:**

```json
{
  "monthly_summary": "| Месяц | Доходы | Расходы | Баланс | ... |",
  "anomalies": [
    {
      "amount": 125000.0,
      "category": "marketing",
      "date": "2024-01-15",
      "z_score": 2.45
    }
  ],
  "trends": {
    "income_trend": "growth",
    "expense_trend": "stable"
  },
  "recommendations": [
    "Слишком высокие расходы по категории 'marketing'..."
  ],
  "health_score": 75
}
```

### API 2: Прогнозирование

```python
@api_view(['GET'])
def forecast_api(request):
    """
    GET /api/forecast/
    
    Возвращает прогноз прибыли на следующий месяц
    """
    from core.ml.forecast import forecast_next_month_profit
    from core.models import Income, Expense
    
    incomes = Income.objects.filter(user=request.user)
    expenses = Expense.objects.filter(user=request.user)
    
    forecast = forecast_next_month_profit(incomes, expenses)
    
    return Response({
        'forecast': forecast,
        'status': 'success' if forecast else 'insufficient_data'
    })
```

**Пример ответа:**

```json
{
  "forecast": 101500.50,
  "status": "success"
}
```

### API 3: Генерация документов

```python
from rest_framework.decorators import api_view
from core.ml.document_generator import generate_document_text
from core.models import Document

@api_view(['POST'])
def generate_document(request):
    """
    POST /api/documents/generate/
    
    Body:
    {
      "type": "invoice",
      "params": {
        "client": "ООО Компания",
        "total": "50000.00",
        "details": "Консультации"
      }
    }
    """
    
    doc_type = request.data.get('type')
    params = request.data.get('params', {})
    
    if not doc_type or not params:
        return Response(
            {'error': 'Missing type or params'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    text = generate_document_text(doc_type, params)
    
    document = Document.objects.create(
        user=request.user,
        doc_type=doc_type,
        params=params,
        generated_text=text
    )
    
    return Response({
        'document_id': document.id,
        'text': text
    }, status=status.HTTP_201_CREATED)
```

---

## Полные сценарии работы

### Сценарий 1: Импорт и анализ финансов

```python
"""
Полный цикл:
1. Пользователь загружает CSV с расходами
2. Система импортирует и автокатегоризирует
3. Система анализирует финансы
4. Возвращает результаты пользователю
"""

from django.views import View
from django.http import JsonResponse
from core.utils.file_ingest import ingest_file
from core.utils.analytics import analyze_finances

class ImportAndAnalyzeView(View):
    def post(self, request):
        # 1. Получить файл
        file = request.FILES['file']
        
        # 2. Импортировать
        try:
            imported_count = ingest_file(request.user, file)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
        
        # 3. Анализировать
        analysis = analyze_finances(request.user)
        
        return JsonResponse({
            'status': 'success',
            'imported': imported_count,
            'analysis': analysis
        })

# Использование:
# POST /api/import-and-analyze/
# Content-Type: multipart/form-data
# File: expenses.csv
```

### Сценарий 2: Полный финансовый отчёт с LLM

```python
"""
Сценарий:
1. Получить анализ финансов
2. Обнаружить аномалии
3. Отправить анализ в LLM для расширенного объяснения
4. Сохранить результаты
"""

def generate_financial_report(user):
    from core.utils.analytics import analyze_finances
    from core.llm import get_llm_response
    from core.models import UserProfile
    
    # Анализ
    analysis = analyze_finances(user)
    
    # Подготовка промпта для LLM
    report_summary = f"""
    Месячные данные:
    {analysis['monthly_summary']}
    
    Аномалии:
    {', '.join(str(a) for a in analysis['anomalies']) or 'Не обнаружены'}
    
    Рекомендации:
    {', '.join(analysis['recommendations'])}
    """
    
    # LLM анализ
    llm_insights = get_llm_response(
        user=user,
        prompt=report_summary,
        system_prompt="Ты финансовый консультант. Проанализируй и дай конкретные советы.",
        anonymize=True,
        use_memory=True
    )
    
    # Сохраняем финансовую память
    profile = UserProfile.objects.get(user=user)
    profile.financial_memory = {
        'last_analysis': analysis,
        'last_report': llm_insights,
        'timestamp': str(datetime.now())
    }
    profile.save()
    
    return {
        'data': analysis,
        'insights': llm_insights,
        'timestamp': datetime.now().isoformat()
    }
```

### Сценарий 3: Автоматическое оповещение при аномалиях

```python
"""
Задача (например, Celery):
- Ежедневно проверять новые расходы
- Если обнаружена аномалия - отправить уведомление
"""

from celery import shared_task
from core.utils.analytics import _detect_expense_anomalies
from core.models import Expense, UserProfile
from django.contrib.auth.models import User
from django.core.mail import send_mail

@shared_task
def check_expense_anomalies():
    """Ежедневная проверка на аномалии"""
    
    for user in User.objects.all():
        expenses = Expense.objects.filter(
            user=user,
            date__gte=timezone.now() - timedelta(days=1)
        ).values('amount', 'category', 'date')
        
        anomalies = _detect_expense_anomalies(list(expenses))
        
        if anomalies:
            # Отправить уведомление
            anomaly_text = "\n".join(
                f"- {a['amount']} на {a['category']} (Z-score: {a['z_score']})"
                for a in anomalies
            )
            
            send_mail(
                'Обнаружены аномальные расходы',
                f"Выявлены необычные расходы:\n{anomaly_text}",
                'noreply@sbfinance.app',
                [user.email],
                fail_silently=True
            )

# Расписание (в settings.py):
# CELERY_BEAT_SCHEDULE = {
#     'check-anomalies': {
#         'task': 'core.tasks.check_expense_anomalies',
#         'schedule': crontab(hour=8, minute=0),  # Каждый день в 8:00
#     },
# }
```

---

## Troubleshooting

### Проблема 1: Модель не загружается

```python
# Проблема:
# ExpenseAutoCategorizer загружается с model=None

# Решение:
from core.ml.train_classifier import train

# Обучить модель:
train()

# Проверить файл:
from pathlib import Path
model_path = Path('media/ml/expense_classifier.joblib')
print(f"Модель существует: {model_path.exists()}")
print(f"Размер: {model_path.stat().st_size if model_path.exists() else 0} байт")
```

### Проблема 2: Недостаточно данных для прогноза

```python
# Проблема: forecast_next_month_profit() возвращает None

# Решение:
from core.models import Income, Expense

user = request.user
incomes = Income.objects.filter(user=user)
expenses = Expense.objects.filter(user=user)

print(f"Доходов: {incomes.count()}")
print(f"Расходов: {expenses.count()}")

# Нужно минимум 2 месяца данных
months = set()
for expense in expenses:
    months.add(expense.date.replace(day=1))
print(f"Месяцев данных: {len(months)}")
```

### Проблема 3: LLM API не отвечает

```python
# Решение:
from core.llm import get_llm_response

try:
    response = get_llm_response(
        user=user,
        prompt="Test",
        timeout=10  # Таймаут
    )
except Exception as e:
    print(f"Ошибка LLM: {e}")
    
    # Fallback: использовать локальный Ollama
    response = get_llm_response(
        user=user,
        prompt="Test",
        force_local=True  # Только локальный режим
    )
```

### Проблема 4: Низкая точность автокатегоризации

```python
# Решение:
# 1. Добавить больше примеров обучения
# 2. Использовать более крупную модель
# 3. Включить настройку параметров

from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

pipe = Pipeline([
    ('tfidf', TfidfVectorizer(
        ngram_range=(1, 3),  # Вместо (1, 2)
        max_features=5000,   # Вместо default
        analyzer='char'      # Вместо 'word'
    )),
    ('clf', LogisticRegression(
        max_iter=5000,
        C=0.1,               # Регуляризация
        class_weight='balanced'
    ))
])
```

---

**Версия документации:** 1.0  
**Дата обновления:** 2024-12-16  
**Ветка Git:** docs-ml-full-description-52x
