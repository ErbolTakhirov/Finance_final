# SB FINANCE AI - Setup & Demo Guide

## Quick Start

### 1. Install Dependencies

```bash
# Ensure you're in the project directory
cd /path/to/sb_finance

# Activate virtual environment
source .venv/bin/activate  # Linux/Mac
# OR
.venv\Scripts\activate  # Windows

# Install/upgrade dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Django settings
DJANGO_SECRET_KEY=your-secret-key-change-me-in-production
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DEBUG=True

# DeepSeek AI (for goal-centric accountant features)
# Leave empty for demo mode (AI will return friendly error messages)
DEEPSEEK_API_URL=https://api.deepseek.com/v1/chat/completions
DEEPSEEK_API_KEY=your-deepseek-api-key-here
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_TIMEOUT_SECONDS=30

# OpenRouter (legacy, fallback)
LLM_API_KEY=your-openrouter-key-here
LLM_API_URL=https://openrouter.ai/api/v1/chat/completions
LLM_MODEL=openai/gpt-4o-mini
```

**Note:** Without AI API keys, the system will still work for transactions, goals, and forecasting. AI advice endpoints will return friendly messages indicating the service is not configured.

### 3. Run Migrations

```bash
python manage.py migrate
```

This will create:
- Core Django tables (auth, sessions, etc.)
- New app tables:
  - `accounts_userprofile` - User profiles with currency/locale
  - `finance_transaction` - Unified income/expense transactions
  - `finance_monthlysummary` - Cached monthly aggregates
  - `finance_categorybudget` - Budget limits
  - `goals_goal` - Financial goals
  - `ai_airec commendationlog` - AI advice history

### 4. Create Demo Data

```bash
python manage.py create_demo_data --username=demo --password=demo12345
```

This creates:
- Demo user (`demo` / `demo12345`)
- 7 months of realistic transaction history
- 2 active financial goals:
  - "Финансовая подушка" (200,000 KGS) - 1 year target
  - "Новый ноутбук" (120,000 KGS) - 240 days target

### 5. Run the Server

```bash
python manage.py runserver
```

Visit: **http://127.0.0.1:8000/**

## Demo Walkthrough

### Authentication

1. **Register a new user**: http://127.0.0.1:8000/accounts/register/
2. **Or login with demo user**:
   - URL: http://127.0.0.1:8000/accounts/login/
   - Username: `demo`
   - Password: `demo12345`

### UI Pages

#### Dashboard (`/dashboard/`)
- **Current month KPIs**: income, expense, profit
- **Active goals**: with progress bars
- **Profit history chart**: Canvas-based line chart
- **AI monthly report button**: Triggers `/api/ai/monthly-report/`

#### Transactions (`/transactions/`)
- **Add transaction form**: date, amount, type (income/expense), category, description
- **Recent transactions table**: last 200 transactions
- **Monthly summaries table**: last 12 months with income/expense/profit
- Link to DRF API for full CRUD

#### Goals (`/goals/`)
- **Create goal form**: title, description, target_amount, target_date
- **Goals list**: all goals with progress bars, status, deadline
- **Goal detail link**: Click to view detailed progress

#### Goal Detail (`/goals/{id}/`)
- **Progress card**:
  - Current saved (sum of all profits)
  - Progress percentage
  - Projected achievement date (based on avg profit trend)
  - Probability of success (0-100%)
- **AI buttons**:
  - "Get AI goal advice" → `/api/ai/goal-advice/`
  - "Get AI forecast explanation" → `/api/ai/forecast/`
- **Profit history chart**

### API Endpoints

#### Finance APIs

```bash
# List transactions (DRF browsable interface)
http://127.0.0.1:8000/api/finance/transactions/

# Create transaction (POST)
curl -u demo:demo12345 -X POST http://127.0.0.1:8000/api/finance/transactions/ \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2025-01-20",
    "amount": "5000.00",
    "type": "income",
    "category": "Bonus",
    "description": "Year-end bonus"
  }'

# Get monthly summaries
http://127.0.0.1:8000/api/finance/monthly-summaries/

# Get category budgets
http://127.0.0.1:8000/api/finance/category-budgets/
```

#### Goals APIs

```bash
# List goals
http://127.0.0.1:8000/api/goals/goals/

# Get goal progress (GET)
curl -u demo:demo12345 http://127.0.0.1:8000/api/goals/goals/1/progress/

# Update goal statuses (POST)
curl -u demo:demo12345 -X POST http://127.0.0.1:8000/api/goals/goals/update_statuses/
```

#### AI APIs

```bash
# Generate monthly report (POST)
curl -u demo:demo12345 -X POST http://127.0.0.1:8000/api/ai/monthly-report/ \
  -H "Content-Type: application/json" \
  -d '{"month_key": "2025-01"}'

# Get goal advice (POST)
curl -u demo:demo12345 -X POST http://127.0.0.1:8000/api/ai/goal-advice/ \
  -H "Content-Type: application/json" \
  -d '{"goal_id": 1}'

# Get profit forecast with AI explanation (POST)
curl -u demo:demo12345 -X POST http://127.0.0.1:8000/api/ai/forecast/ \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Response format** (if ≥3 months of data):
```json
{
  "status": "ok",
  "predicted_profit": "15234.56",
  "lower": "12000.00",
  "upper": "18000.00",
  "algorithm": "linear_regression_profit_trend",
  "used_months": 7,
  "explanation": "AI-generated text explaining the trend..."
}
```

**Response format** (if <3 months):
```json
{
  "status": "insufficient_data",
  "message": "Требуется минимум 3 месяца данных для прогноза"
}
```

## Running Tests

```bash
# Run all tests for new apps
python manage.py test finance goals

# Run with verbose output
python manage.py test finance goals --verbosity=2

# Run specific test
python manage.py test finance.tests.ForecastServiceTests
```

**Test coverage:**
- ✅ MonthlySummary recalculation (income + expense → profit)
- ✅ ForecastService with <3 months (returns insufficient_data)
- ✅ ForecastService with ≥3 months (returns predicted_profit with bounds)
- ✅ Goal progress calculation (current_saved, progress_percent)
- ✅ Auto status updates (achieved/failed based on conditions)

## Architecture Overview

### Apps

1. **accounts** - User profiles (currency, locale, privacy settings)
2. **finance** - Transactions, monthly summaries, budgets + services
3. **goals** - Financial goals with progress tracking
4. **ai** - DeepSeek integration and recommendation logs
5. **core** (legacy) - Backward compatibility with existing features

### Service Layer

- `finance.services.accounting.AccountingService`
  - CRUD for transactions with automatic monthly summary recalculation
- `finance.services.forecast.ForecastService`
  - Linear regression on profit trend (requires ≥3 months)
- `goals.services.GoalService`
  - Goal CRUD, progress calculation, auto status updates
- `ai.services.AIService`
  - DeepSeek API integration with error handling

### Key Business Logic

#### MonthlySummary Calculation
```python
total_income = sum(transactions where type='income' and month_key=X)
total_expense = sum(transactions where type='expense' and month_key=X)
profit = total_income - total_expense
```

#### Profit Forecasting (Linear Regression)
```python
# Requires ≥3 months of MonthlySummary data
profits = [month1.profit, month2.profit, month3.profit, ...]
x = [0, 1, 2, ...]
coefficients = polyfit(x, profits, degree=1)  # y = mx + b
predicted_profit = polyval(coefficients, len(profits))  # Next month

# Confidence interval (80%)
std_dev = std(residuals)
lower = predicted_profit - 1.28 * std_dev
upper = predicted_profit + 1.28 * std_dev
```

#### Goal Progress
```python
current_saved = sum(all_profits_for_user)
progress_percent = (current_saved / target_amount) * 100

# Projections
avg_profit_last_3_months = avg([m1.profit, m2.profit, m3.profit])
remaining = target_amount - current_saved
months_needed = remaining / avg_profit_last_3_months
projected_date = today + (months_needed * 30 days)

# Probability
months_left = (target_date - today) / 30
if months_needed <= months_left:
    probability = 70 + (months_left - months_needed) * 10  # On track
else:
    probability = 50 - (months_needed - months_left) * 10  # Behind
```

## Troubleshooting

### "No such table" errors
Run migrations:
```bash
python manage.py migrate
```

### "AI service not configured" messages
- Set `DEEPSEEK_API_URL` and `DEEPSEEK_API_KEY` in `.env`
- Or use without AI (transactions and goals will still work)

### Login redirect issues
Check that `LOGIN_REDIRECT_URL = '/dashboard/'` in `settings.py`

### Static files not loading
Run:
```bash
python manage.py collectstatic
```

### Demo data already exists
Delete and recreate:
```bash
python manage.py shell
>>> from django.contrib.auth.models import User
>>> User.objects.filter(username='demo').delete()
>>> exit()
python manage.py create_demo_data
```

## Next Steps

1. **Add more transactions**: Use UI or API
2. **Create personal goals**: Set realistic targets
3. **Configure AI keys**: Get real AI advice
4. **Deploy to production**: Follow `DEPLOYMENT.md` (if exists)
5. **Customize**: Extend models, add recurring transactions, budgets, etc.

## Documentation

- **Architecture**: See `ARCHITECTURE.md` for detailed system design
- **Goal-Centric Features**: See `README_GOAL_CENTRIC.md`
- **Original README**: See `README.md` for legacy features

---

**Built with Django 4.2+ and Django REST Framework 3.15+**

For issues or questions, check the code or documentation files.
