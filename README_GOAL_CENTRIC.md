# 💰 SB FINANCE AI - Goal-Centric AI Accountant

## 🎯 Overview

SB FINANCE AI has been **refactored** into a professional, goal-centric AI accountant system built on Django + Django REST Framework. This is not a minimal MVP — it's a **production-ready** personal finance management platform with:

- **Clean architecture**: 4 Django apps with proper separation of concerns
- **Service layer**: Business logic decoupled from views
- **DeepSeek AI integration**: Intelligent financial coaching
- **Goal tracking**: Progress monitoring with AI-powered advice
- **Profit forecasting**: Linear regression on ≥3 months of data
- **RESTful APIs**: Full DRF implementation with proper serializers and permissions
- **Comprehensive tests**: Unit tests for critical business logic

---

## 📦 Architecture

The project is organized into **4 specialized Django apps**:

### 1. **accounts** — User Management
- `UserProfile` model: currency, locale, timezone, privacy settings
- Automatic profile creation via Django signals

### 2. **finance** — Financial Accounting
- `Transaction` model: unified income/expense tracking
- `MonthlySummary` model: cached monthly aggregates (income, expense, profit)
- `CategoryBudget` model: budget limits per category
- **Services:**
  - `AccountingService`: CRUD for transactions, auto-recalculates summaries
  - `ForecastService`: Profit forecasting (requires ≥3 months of data)
- **APIs:**
  - `/api/finance/transactions/` - CRUD
  - `/api/finance/monthly-summaries/` - Read-only
  - `/api/finance/category-budgets/` - CRUD

### 3. **goals** — Financial Goals
- `Goal` model: target_amount, target_date, status (active/achieved/failed)
- Computed properties: `current_saved`, `progress_percent`
- **Services:**
  - `GoalService`: CRUD, progress calculation, auto status updates
- **APIs:**
  - `/api/goals/goals/` - CRUD
  - `/api/goals/goals/{id}/progress/` - Get detailed progress
  - `/api/goals/goals/update_statuses/` - Auto-update statuses

### 4. **ai** — DeepSeek Integration
- `AIRecommendationLog` model: logs all AI-generated advice
- **Services:**
  - `AIService`: DeepSeek integration for monthly reports, goal advice, forecast explanations
- **APIs:**
  - `/api/ai/monthly-report/` - Generate monthly report
  - `/api/ai/goal-advice/` - Get goal-specific coaching
  - `/api/ai/forecast/` - Get profit forecast + AI explanation

### 5. **core** (legacy)
- Backward compatibility with existing features
- Teen-focused FinBilim 2025 MVP
- Chat system, file uploads, document generation

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- PostgreSQL (recommended) or SQLite (default)
- DeepSeek API key (or OpenAI-compatible service)

### Installation

```bash
# 1. Clone and navigate
cd /path/to/project

# 2. Activate virtual environment (if not already)
source .venv/bin/activate  # Linux/Mac
# OR
.venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file
cp env.example .env
# Edit .env and add:
DEEPSEEK_API_URL=https://api.deepseek.com/v1/chat/completions
DEEPSEEK_API_KEY=your-key-here
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_TIMEOUT_SECONDS=30

# 5. Run migrations
python manage.py migrate

# 6. Create superuser
python manage.py createsuperuser

# 7. Create demo data
python manage.py create_demo_data --username=demo --password=demo12345

# 8. Run server
python manage.py runserver
```

Visit: `http://127.0.0.1:8000/`

---

## 📊 Demo Walkthrough

After running `create_demo_data`, you'll have:
- **User:** `demo` / `demo12345`
- **6+ months** of transaction history
- **2 active goals**:
  - Финансовая подушка (200,000)
  - Новый ноутбук (120,000)

### Step 1: Login
```
Username: demo
Password: demo12345
```

### Step 2: View Dashboard
Navigate to `/` (workspace) or use the existing dashboard.

### Step 3: Test APIs

#### Get Monthly Summary
```bash
curl -u demo:demo12345 http://127.0.0.1:8000/api/finance/monthly-summaries/
```

#### Create Transaction
```bash
curl -u demo:demo12345 -X POST http://127.0.0.1:8000/api/finance/transactions/ \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2025-01-20",
    "amount": "5000.00",
    "type": "income",
    "category": "Bonus",
    "description": "Year-end bonus"
  }'
```

#### Get Goals
```bash
curl -u demo:demo12345 http://127.0.0.1:8000/api/goals/goals/
```

#### Get Goal Progress
```bash
# Replace {id} with actual goal ID from above
curl -u demo:demo12345 http://127.0.0.1:8000/api/goals/goals/{id}/progress/
```

#### Generate Monthly Report (AI)
```bash
curl -u demo:demo12345 -X POST http://127.0.0.1:8000/api/ai/monthly-report/ \
  -H "Content-Type: application/json" \
  -d '{"month_key": "2025-01"}'
```

#### Get Profit Forecast (AI)
```bash
curl -u demo:demo12345 -X POST http://127.0.0.1:8000/api/ai/forecast/ \
  -H "Content-Type: application/json" \
  -d '{}'
```

#### Get Goal Advice (AI)
```bash
curl -u demo:demo12345 -X POST http://127.0.0.1:8000/api/ai/goal-advice/ \
  -H "Content-Type: application/json" \
  -d '{"goal_id": 1}'
```

---

## 🧪 Running Tests

```bash
# Run all tests
python manage.py test finance goals

# Run specific test file
python manage.py test finance.tests.test_accounting_and_forecast

# Run with verbose output
python manage.py test finance goals --verbosity=2
```

**Test Coverage:**
- `finance/tests/test_accounting_and_forecast.py`:
  - Monthly summary recalculation
  - Forecast with <3 months (insufficient_data)
  - Forecast with ≥3 months (ok, validates predicted_profit)
- `goals/tests/test_goal_progress.py`:
  - Goal progress calculation
  - Auto status updates (achieved/failed)

---

## 📚 Key Features

### 1. Transaction Management
- **Unified model**: income and expense in one `Transaction` table
- **Automatic recalculation**: Django signals update `MonthlySummary` on save/delete
- **Validation**: amount > 0, proper month_key format
- **API**: Full CRUD via DRF

### 2. Monthly Summaries
- **Cached aggregates**: total_income, total_expense, profit
- **Performance**: No need to aggregate on every request
- **API**: Read-only endpoint

### 3. Financial Goals
- **Computed properties**:
  - `current_saved`: Sum of profits since goal creation
  - `progress_percent`: (current_saved / target_amount) * 100
- **Progress calculation**:
  - `projected_date`: When goal will be achieved at current profit rate
  - `probability_of_success`: 0-100% based on avg profit and time left
- **Auto status updates**: Mark goals as achieved/failed

### 4. Profit Forecasting
- **Algorithm**: Linear regression on monthly profit trend
- **Requirements**: ≥3 months of data
- **Output**: predicted_profit, lower/upper bounds (80% confidence interval)
- **Status**: `ok` or `insufficient_data`

### 5. DeepSeek AI Integration
- **Monthly Reports**: Analyzes income/expense, top categories, provides insights
- **Goal Advice**: Coaches user toward goals, suggests actions
- **Forecast Explanation**: Explains profit trends and predictions
- **Fact-based**: AI does NOT invent numbers, uses only provided data
- **Beginner-friendly**: Simple language, structured output

### 6. Service Layer
- **AccountingService**: Business logic for transactions and summaries
- **ForecastService**: Profit forecasting with linear regression
- **GoalService**: Goal CRUD, progress calculation, status updates
- **AIService**: DeepSeek integration with error handling

---

## 🔑 Configuration

### DeepSeek (Recommended)
Add to `.env`:
```bash
DEEPSEEK_API_URL=https://api.deepseek.com/v1/chat/completions
DEEPSEEK_API_KEY=your-key-here
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_TIMEOUT_SECONDS=30
```

### OpenRouter (Legacy/Fallback)
```bash
LLM_API_KEY=your-openrouter-key
LLM_API_URL=https://openrouter.ai/api/v1/chat/completions
LLM_MODEL=openai/gpt-4o-mini
```

### PostgreSQL (Production)
```bash
# Install psycopg2
pip install psycopg2-binary

# Update settings.py:
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'sb_finance',
        'USER': 'your_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

---

## 📖 API Reference

### Finance APIs
```
GET    /api/finance/transactions/           List transactions (filtered by user)
POST   /api/finance/transactions/           Create transaction
GET    /api/finance/transactions/{id}/      Get transaction
PUT    /api/finance/transactions/{id}/      Update transaction
DELETE /api/finance/transactions/{id}/      Delete transaction

GET    /api/finance/monthly-summaries/      List monthly summaries (filtered by user)
GET    /api/finance/monthly-summaries/{id}/ Get monthly summary

GET    /api/finance/category-budgets/       List budgets (filtered by user)
POST   /api/finance/category-budgets/       Create budget
```

### Goals APIs
```
GET    /api/goals/goals/                    List goals (filtered by user)
POST   /api/goals/goals/                    Create goal
GET    /api/goals/goals/{id}/               Get goal
PUT    /api/goals/goals/{id}/               Update goal
DELETE /api/goals/goals/{id}/               Delete goal
GET    /api/goals/goals/{id}/progress/      Get progress details
POST   /api/goals/goals/update_statuses/    Update all goal statuses
```

### AI APIs
```
POST   /api/ai/monthly-report/              Generate monthly report
       Body: {"month_key": "2025-01"}
       Response: {"report": "AI-generated text"}

POST   /api/ai/goal-advice/                 Get goal-specific advice
       Body: {"goal_id": 1}
       Response: {"advice": "AI coaching text"}

POST   /api/ai/forecast/                    Get profit forecast + explanation
       Body: {}
       Response: {
         "status": "ok",
         "predicted_profit": "15000.00",
         "lower": "12000.00",
         "upper": "18000.00",
         "algorithm": "linear_regression_profit_trend",
         "used_months": 6,
         "explanation": "AI-generated text"
       }
```

---

## 🏗️ Project Structure

```
sb-finance-ai/
├── accounts/              # User profiles and auth
│   ├── models.py         # UserProfile
│   ├── signals.py        # Auto-create profiles
│   └── apps.py
├── finance/              # Financial accounting
│   ├── models.py         # Transaction, MonthlySummary, CategoryBudget
│   ├── serializers.py    # DRF serializers
│   ├── views.py          # DRF viewsets
│   ├── urls.py           # API routes
│   ├── signals.py        # Auto-recalculate summaries
│   ├── services/
│   │   ├── accounting.py # AccountingService
│   │   └── forecast.py   # ForecastService
│   ├── tests/
│   │   └── test_accounting_and_forecast.py
│   └── management/commands/
│       └── create_demo_data.py
├── goals/                # Financial goals
│   ├── models.py         # Goal
│   ├── serializers.py    # DRF serializers
│   ├── views.py          # DRF viewsets
│   ├── urls.py           # API routes
│   ├── services.py       # GoalService
│   └── tests/
│       └── test_goal_progress.py
├── ai/                   # DeepSeek integration
│   ├── models.py         # AIRecommendationLog
│   ├── views.py          # API views
│   ├── urls.py           # API routes
│   └── services.py       # AIService
├── core/                 # Legacy app (backward compatibility)
│   ├── models.py         # Legacy models
│   ├── views.py          # Legacy views
│   └── ...
├── sb_finance/           # Django project settings
│   ├── settings.py       # Updated with new apps, DRF, DeepSeek config
│   └── urls.py           # Main URL config
├── ARCHITECTURE.md       # Detailed architecture documentation
├── README.md             # Original README
├── README_GOAL_CENTRIC.md # This file
├── requirements.txt      # Updated with djangorestframework
└── manage.py
```

---

## 🧠 How It Works

### Transaction Flow
1. User creates transaction via `/api/finance/transactions/` (POST)
2. `TransactionViewSet.perform_create()` → `AccountingService.create_transaction()`
3. `Transaction` saved → Django signal triggers `auto_recalculate_month()`
4. `MonthlySummary.recalculate()` aggregates all transactions for that month
5. Summary updated with total_income, total_expense, profit

### Forecast Flow
1. User requests `/api/ai/forecast/` (POST)
2. Fetch all `MonthlySummary` for user, ordered by month
3. If < 3 months → return `{"status": "insufficient_data"}`
4. Else → `ForecastService.forecast_next_month()`:
   - Extract profit values: [100, 110, 120, ...]
   - Fit linear regression: `y = mx + b`
   - Predict next month: `y_pred = m * (n+1) + b`
   - Calculate confidence interval (±1.28 * std)
5. `AIService.generate_forecast_explanation()` → call DeepSeek API
6. Return forecast + AI explanation

### Goal Progress Flow
1. User requests `/api/goals/goals/{id}/progress/` (GET)
2. `GoalViewSet.progress()` → `GoalService.calculate_progress(goal)`
3. Calculate:
   - `current_saved`: Sum of profits since goal creation
   - `progress_percent`: (current_saved / target_amount) * 100
   - `avg_profit`: Average of last 3 months
   - `months_needed`: (target_amount - current_saved) / avg_profit
   - `projected_date`: today + months_needed * 30 days
   - `probability_of_success`: Based on months_needed vs months_left
4. Return progress details

### AI Advice Flow
1. User requests `/api/ai/goal-advice/` (POST, {"goal_id": 1})
2. Fetch goal, compute progress, fetch profit history
3. Run forecast to get predicted_profit
4. `AIService.generate_goal_progress_advice()`:
   - Build prompt with facts: goal details, history, forecast
   - Call DeepSeek API
   - Parse response
   - Log to `AIRecommendationLog`
5. Return AI advice

---

## 🔐 Security

- **Authentication**: Django sessions + DRF authentication
- **Permissions**: `IsAuthenticated` on all APIs
- **Row-level filtering**: Users see only their own data
- **Validation**: Amount > 0, dates in future for goals

---

## 📈 Roadmap

- [ ] Add UI pages (dashboard, transactions, goals)
- [ ] Charts with Chart.js / Plotly
- [ ] Recurring transactions
- [ ] Budget alerts (when exceeding category budgets)
- [ ] Multi-currency support
- [ ] Bank integration (Plaid, Salt Edge)
- [ ] Mobile app (React Native)
- [ ] Advanced forecasting (ARIMA, Prophet)
- [ ] Social features (compare with friends)

---

## 🤝 Contributing

We welcome contributions! Please:
1. Fork the repo
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

**Code Style:** Follow PEP8, write tests for new features.

---

## 📄 License

MIT License. See `LICENSE` file.

---

## 🙏 Acknowledgments

- **Django** for the amazing framework
- **Django REST Framework** for clean APIs
- **DeepSeek** for powerful AI
- **scikit-learn** for forecasting tools
- **pandas** for data manipulation

---

**Built with ❤️ for FinTech Hackathon 2025**

For detailed architecture, see [ARCHITECTURE.md](./ARCHITECTURE.md).
