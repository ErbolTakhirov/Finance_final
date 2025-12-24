# SB FINANCE AI - Architecture Documentation

## Overview
SB FINANCE AI is a **goal-centric AI accountant** — a Django-based personal finance management system with integrated AI assistance powered by DeepSeek (or any OpenAI-compatible LLM service).

## Tech Stack

**Backend:**
- Django 4.2+ (Python 3.9+)
- Django REST Framework 3.15+ for APIs
- PostgreSQL-ready (defaults to SQLite)

**Data Science:**
- pandas, NumPy for data analysis
- scikit-learn for forecasting (linear regression)
- matplotlib/plotly for charts

**AI Integration:**
- DeepSeek (or OpenAI-compatible API) for advice generation
- Fallback to OpenRouter for legacy features
- Support for local Ollama

**Infrastructure:**
- python-dotenv for configuration
- requests for HTTP communication

## App Structure

### 1. `accounts` - User Management
**Models:**
- `UserProfile`: extends Django User with currency, locale, timezone, privacy settings

**Purpose:**
- Centralized user profile management
- Privacy preferences (anonymize, use_local_llm)

### 2. `finance` - Financial Accounting
**Models:**
- `Transaction`: unified income/expense transactions with validation
- `MonthlySummary`: cached monthly aggregates (income, expense, profit)
- `CategoryBudget`: budget limits per category

**Services:**
- `AccountingService`: CRUD for transactions, auto-recalculates monthly summaries
- `ForecastService`: profit forecasting using linear regression (requires ≥3 months)

**API Endpoints:**
- `/api/finance/transactions/` - CRUD transactions
- `/api/finance/monthly-summaries/` - Read monthly summaries
- `/api/finance/category-budgets/` - Manage budgets

**Features:**
- Automatic `MonthlySummary` recalculation via Django signals
- Proper validation (amount > 0, proper dates)
- Top expense categories by month

### 3. `goals` - Financial Goals
**Models:**
- `Goal`: financial goals with target_amount, target_date, status (active/achieved/failed)

**Computed Properties:**
- `current_saved`: sum of profits since goal creation
- `progress_percent`: (current_saved / target_amount) * 100

**Services:**
- `GoalService`: CRUD, progress calculation, auto status updates
  - `calculate_progress()`: computes projected_date and probability_of_success
  - `auto_update_statuses()`: marks goals as achieved/failed

**API Endpoints:**
- `/api/goals/goals/` - CRUD goals
- `/api/goals/goals/{id}/progress/` - Get detailed progress
- `/api/goals/goals/update_statuses/` - Auto-update statuses

### 4. `ai` - DeepSeek Integration
**Models:**
- `AIRecommendationLog`: logs all AI-generated advice with user, goal, month_key, type

**Services:**
- `AIService`: integrates with DeepSeek (or any OpenAI-compatible endpoint)
  - `generate_monthly_report()`: analyzes month data, returns insights
  - `generate_goal_progress_advice()`: coaches user toward goals
  - `generate_forecast_explanation()`: explains profit forecast

**API Endpoints:**
- `/api/ai/monthly-report/` - POST: generate monthly report
- `/api/ai/goal-advice/` - POST: get goal-specific advice
- `/api/ai/forecast/` - POST: get profit forecast + AI explanation

**Configuration (.env):**
```
DEEPSEEK_API_URL=https://api.deepseek.com/v1/chat/completions
DEEPSEEK_API_KEY=your-key-here
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_TIMEOUT_SECONDS=30
```

**AI Prompts:**
- Strictly fact-based: AI does NOT invent numbers
- Explains data in simple, beginner-friendly language
- Provides 2-3 actionable tips

### 5. `core` (legacy)
**Purpose:**
- Backward compatibility with existing features
- Teen-focused FinBilim 2025 MVP (gamification, learning, scam detection)
- Chat system, file uploads, document generation

**Note:** The refactored apps (`finance`, `goals`, `ai`, `accounts`) coexist with `core` to preserve existing functionality.

## Data Flow

### Transaction Creation Flow
1. User creates transaction via `/api/finance/transactions/` (POST)
2. `TransactionViewSet.perform_create()` → `AccountingService.create_transaction()`
3. `Transaction` saved → signal `post_save` → `auto_recalculate_month()`
4. `MonthlySummary.recalculate()` → aggregates income/expense → stores profit
5. Response returned to user

### Monthly Report Flow
1. User requests `/api/ai/monthly-report/` (POST) with `month_key`
2. Fetch `MonthlySummary` and top expense categories via `AccountingService`
3. `AIService.generate_monthly_report()` → calls DeepSeek API
4. AI analyzes data → returns insights
5. Logs to `AIRecommendationLog`
6. Response returned

### Goal Advice Flow
1. User requests `/api/ai/goal-advice/` (POST) with `goal_id`
2. Fetch `Goal`, compute progress via `GoalService.calculate_progress()`
3. Fetch profit history, run `ForecastService.forecast_next_month()`
4. `AIService.generate_goal_progress_advice()` → calls DeepSeek
5. AI provides coaching
6. Logs to `AIRecommendationLog`
7. Response returned

### Forecast Flow
1. User requests `/api/ai/forecast/` (POST)
2. Fetch all `MonthlySummary` for user
3. `ForecastService.forecast_next_month()`:
   - If < 3 months → return "insufficient_data"
   - Else → linear regression on profit trend
   - Return predicted_profit, lower, upper bounds
4. `AIService.generate_forecast_explanation()` → calls DeepSeek
5. AI explains trend and recommendations
6. Response returned

## Key Business Logic

### ForecastService Algorithm
```python
# Linear regression on profit trend
profits = [s.profit for s in history]
x = [0, 1, 2, ...]
coef = polyfit(x, profits, 1)  # y = mx + b
predicted = polyval(coef, len(profits))

# Confidence interval (80%)
std = std(residuals)
lower = predicted - 1.28 * std
upper = predicted + 1.28 * std
```

### GoalService Progress Calculation
```python
# Current saved = sum of profits since goal created
current = sum(profits for month >= goal.created_month)

# Projected date if current trend continues
avg_profit = avg(last_3_months.profit)
months_needed = (target_amount - current) / avg_profit
projected_date = today + months_needed * 30 days

# Probability of success
months_left = (target_date - today) / 30
if months_needed <= months_left:
    probability = 70 + (months_left - months_needed) * 10
else:
    probability = 50 - (months_needed - months_left) * 10
```

## Database Schema

### Core Tables
- `accounts_userprofile`: user settings
- `finance_transaction`: all income/expense records
- `finance_monthlysummary`: cached monthly aggregates
- `finance_categorybudget`: budget limits
- `goals_goal`: financial goals
- `ai_airrecommendationlog`: AI advice history

### Key Indexes
- `(user, date)` on transactions
- `(user, month_key)` on transactions and summaries
- `(user, status)` on goals

## Security & Privacy

### Authentication
- Django sessions + DRF authentication
- All APIs require `IsAuthenticated`
- Row-level filtering: users see only their own data

### Anonymization (legacy feature)
- Optional anonymization before sending to cloud LLM (via `UserProfile.auto_anonymize`)
- Local LLM option (Ollama) for sensitive data

## Testing

### Unit Tests
- `finance/tests/test_accounting_and_forecast.py`:
  - MonthlySummary recalculation
  - Forecast with <3 months (insufficient_data)
  - Forecast with ≥3 months (ok)
- `goals/tests/test_goal_progress.py`:
  - Goal progress calculation
  - Auto status updates (achieved/failed)

### Run Tests
```bash
python manage.py test finance goals
```

## Deployment

### Environment Variables
```bash
# Django
DJANGO_SECRET_KEY=your-secret-key
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DEBUG=False

# Database (PostgreSQL recommended for production)
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# DeepSeek AI
DEEPSEEK_API_URL=https://api.deepseek.com/v1/chat/completions
DEEPSEEK_API_KEY=your-deepseek-key
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_TIMEOUT_SECONDS=30

# Legacy LLM (OpenRouter)
LLM_API_KEY=your-openrouter-key
LLM_API_URL=https://openrouter.ai/api/v1/chat/completions
LLM_MODEL=openai/gpt-4o-mini
```

### Production Checklist
- Set `DEBUG=False`
- Use PostgreSQL
- Configure `ALLOWED_HOSTS`
- Set strong `SECRET_KEY`
- Run `python manage.py collectstatic`
- Run migrations: `python manage.py migrate`
- Use gunicorn/uwsgi + nginx
- Enable HTTPS

## API Reference

### Finance APIs
```
GET    /api/finance/transactions/           List transactions
POST   /api/finance/transactions/           Create transaction
GET    /api/finance/transactions/{id}/      Get transaction
PUT    /api/finance/transactions/{id}/      Update transaction
DELETE /api/finance/transactions/{id}/      Delete transaction

GET    /api/finance/monthly-summaries/      List monthly summaries
GET    /api/finance/category-budgets/       List budgets
POST   /api/finance/category-budgets/       Create budget
```

### Goals APIs
```
GET    /api/goals/goals/                    List goals
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
       
POST   /api/ai/goal-advice/                 Get goal-specific advice
       Body: {"goal_id": 1}
       
POST   /api/ai/forecast/                    Get profit forecast + explanation
       Body: {}
```

## UI (Templates)

### Existing UI (legacy)
- `/` - Dashboard (workspace)
- `/expense/`, `/income/` - Transaction management
- `/documents/` - Document generation
- `/ai/` - AI recommendations

### Goal-Centric UI (to be added)
- Dashboard with:
  - Current month KPIs (income, expense, profit)
  - Active goals with progress bars
  - "AI Report" button → triggers `/api/ai/monthly-report/`
- Transactions page:
  - List of all transactions
  - Filter by type, category, month
  - Add/edit/delete transactions
- Goals page:
  - List of all goals
  - Detail page per goal:
    - Progress bar (current_saved / target_amount)
    - Chart of monthly profits
    - AI advice section → triggers `/api/ai/goal-advice/`
    - Forecast section → triggers `/api/ai/forecast/`

## Future Enhancements

1. **Smart Budgeting**: Auto-suggest budgets based on past spending
2. **Real-time Notifications**: Alerts when approaching budget limits
3. **Multiple Currencies**: Support for multi-currency transactions
4. **Recurring Transactions**: Auto-create monthly bills
5. **Bank Integration**: Import transactions from bank APIs
6. **Advanced Forecasting**: ARIMA, Prophet for seasonal trends
7. **Goal Templates**: Pre-defined goals (emergency fund, vacation, etc.)
8. **Social Features**: Compare progress with friends (anonymized)
9. **Mobile App**: React Native / Flutter frontend
10. **Webhook Support**: Notify external systems on goal achievement

---

**Last Updated:** 2025-01-18
**Version:** 2.0 (Goal-Centric Refactor)
