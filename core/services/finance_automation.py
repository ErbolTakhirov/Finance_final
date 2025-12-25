import json
import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from django.db.models import Sum, Q
from django.utils import timezone
from core.models import Income, Expense, UserGoal, FinancialInsight
from core.ai_services.llm_manager import llm_manager

logger = logging.getLogger(__name__)

class FinanceAutomationService:
    """
    Core service for the "AI Accountant" features.
    Handles data parsing, AI categorization, and smart analytics.
    """

    CATEGORIES = {
        'expense': [
            'food', 'transport', 'entertainment', 'shopping', 
            'subscriptions', 'education', 'health', 'beauty', 
            'games', 'rent', 'marketing', 'software', 
            'equipment', 'tax', 'other'
        ],
        'income': [
            'allowance', 'part_time', 'gift', 'freelance', 
            'sales', 'investment', 'services', 'salary', 
            'bonus', 'other'
        ]
    }

    @staticmethod
    def parse_raw_text(text: str) -> List[Dict[str, Any]]:
        """
        Parses raw text like "01.12 Magnit 450r, 02.12 Yandex 320r"
        Returns a list of structured transaction candidates.
        """
        lines = re.split(r'[,\n;]+', text)
        parsed_results = []
        
        current_year = datetime.now().year
        
        for line in lines:
            line = line.strip()
            if not line: continue
            
            # Simple regex to find amount (digits + optional decimal) and text
            # Matches: "01.12 Magnit 450", "320р ЯндексТакси", "1500.50 перевод"
            amount_match = re.search(r'(\d+[.,]?\d*)', line)
            date_match = re.search(r'(\d{2}\.\d{2})', line)
            
            if amount_match:
                amount_str = amount_match.group(1).replace(',', '.')
                try:
                    amount = float(amount_str)
                except ValueError:
                    amount = 0.0
                
                # Try to extract date
                tx_date = timezone.now().date()
                if date_match:
                    try:
                        day, month = map(int, date_match.group(1).split('.'))
                        tx_date = datetime(current_year, month, day).date()
                    except (ValueError, TypeError):
                        pass
                
                # Description is everything else
                desc = line.replace(amount_match.group(0), '').replace(date_match.group(0) if date_match else '', '').strip()
                # Clean description from currency symbols like 'р', 'сом', 'rub', '$'
                desc = re.sub(r'(р|руб|сом|kgs|rub|\$|€)', '', desc, flags=re.I).strip()
                
                parsed_results.append({
                    'raw': line,
                    'date': tx_date,
                    'amount': amount,
                    'description': desc or "Транзакция",
                    'merchant': desc or "Мерчант",
                    'needs_review': True # Mark for AI to check or user to confirm
                })
        
        return parsed_results

    async def categorize_with_ai(self, transactions: List[Dict[str, Any]], user) -> List[Dict[str, Any]]:
        """
        Uses LLM to categorize a batch of transactions.
        """
        if not transactions:
            return []

        prompt = f"""
Ты - AI бухгалтер. Категоризируй следующие транзакции для подростка.
Для каждой транзакции определи:
1. Тип (income или expense)
2. Категорию из списка ниже.
3. Уточни мерчанта (название магазина или сервиса).

СПИСОК КАТЕГОРИЙ РАСХОДОВ: {", ".join(self.CATEGORIES['expense'])}
СПИСОК КАТЕГОРИЙ ДОХОДОВ: {", ".join(self.CATEGORIES['income'])}

ТРАНЗАКЦИИ:
{json.dumps([{ 'desc': t['description'], 'amt': t['amount']} for t in transactions], ensure_ascii=False)}

ОТВЕТЬ ТОЛЬКО В ГОРЯЧЕМ JSON МАССИВЕ вида:
[
  {{"type": "expense", "category": "food", "merchant": "Магнит", "confidence": 0.95}},
  ...
]
"""
        try:
            response = await llm_manager.chat([
                {"role": "system", "content": "You are a professional financial categorizer robot."},
                {"role": "user", "content": prompt}
            ], temperature=0.1)
            
            # Extract JSON from response (sometimes LLM adds markdown)
            json_str = re.search(r'\[.*\]', response.content, re.DOTALL)
            if json_str:
                ai_results = json.loads(json_str.group(0))
                
                # Merge AI results with original data
                for i, result in enumerate(ai_results):
                    if i < len(transactions):
                        transactions[i].update({
                            'type': result.get('type', 'expense'),
                            'category': result.get('category', 'other'),
                            'merchant': result.get('merchant', transactions[i]['merchant']),
                            'confidence': result.get('confidence', 0.5),
                            'needs_review': result.get('confidence', 1.0) < 0.8
                        })
            return transactions
        except Exception as e:
            logger.error(f"AI Categorization error: {e}")
            # Fallback to simple rule-based categorization
            return self.fallback_categorization(transactions)

    def fallback_categorization(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Simple rule-based categorization if AI fails."""
        for t in transactions:
            desc = t['description'].lower()
            t['type'] = 'expense'
            t['category'] = 'other'
            
            if any(word in desc for word in ['еда', 'бургер', 'кфс', 'магнит', 'пятерочка', 'food']):
                t['category'] = 'food'
            elif any(word in desc for word in ['такси', 'автобус', 'метро', 'uber', 'yandex']):
                t['category'] = 'transport'
            elif any(word in desc for word in ['курс', 'учеба', 'школа', 'education']):
                t['category'] = 'education'
            
            t['needs_review'] = True
        return transactions

    def get_money_leaks(self, user, days=30) -> List[Dict[str, Any]]:
        """Identify top spending categories (potential leaks)."""
        start_date = timezone.now().date() - timezone.timedelta(days=days)
        leaks = Expense.objects.filter(user=user, date__gte=start_date) \
            .values('expense_type') \
            .annotate(total=Sum('amount')) \
            .order_by('-total')
        
        return list(leaks)

    async def generate_ai_advice(self, user) -> str:
        """Generates personalized, friendly financial advice for teens."""
        leaks = self.get_money_leaks(user)
        forecast = self.get_forecast(user)
        goals = user.goals.filter(status='active')
        
        context = {
            "top_spending": leaks[:3],
            "forecast": forecast,
            "goals": [{"title": g.title, "progress": g.progress_percentage()} for g in goals]
        }
        
        prompt = f"""
Ты - крутой финансовый наставник для подростков. Проанализируй данные и дай 3 конкретных, мотивирующих совета.
Используй молодежный сленг (но вмеру), будь на одной волне.
ДАННЫЕ: {json.dumps(context, ensure_ascii=False)}

ФОРМАТ ОТВЕТА: Только текст советов (без вводных фраз "Вот ваши советы"). Каждое предложение с новой строки.
"""
        try:
            response = await llm_manager.chat([
                {"role": "system", "content": "You are a friendly teen financial coach."},
                {"role": "user", "content": prompt}
            ], temperature=0.7)
            return response.content
        except Exception as e:
            logger.error(f"AI Advisor error: {e}")
            return "Твои финансы в порядке! Продолжай следить за тратами и ты обязательно достигнешь своих целей."

    def parse_csv(self, file_content: str) -> List[Dict[str, Any]]:
        """Parses CSV content from bank exports."""
        import csv
        import io
        f = io.StringIO(file_content)
        reader = csv.DictReader(f)
        results = []
        for row in reader:
            # Try to find amount and date in common bank formats
            amount = 0.0
            for key in ['amount', 'sum', 'сумма', 'цена']:
                if key in row:
                    try: amount = float(row[key].replace(',', '.'))
                    except: pass
            
            desc = row.get('description', row.get('merchant', row.get('назначение', 'Транзакция')))
            
            results.append({
                'date': timezone.now().date(), # Fallback
                'amount': abs(amount),
                'description': desc,
                'merchant': desc,
                'type': 'expense' if amount < 0 else 'income',
                'needs_review': True
            })
        return results

    def link_transaction_to_goal(self, user, transaction, goal_id):
        """Links a transaction to a specific goal and updates its progress."""
        goal = UserGoal.objects.get(id=goal_id, user=user)
        if transaction.income_type or (hasattr(transaction, 'type') and transaction.type == 'income'):
            goal.current_amount += transaction.amount
            goal.save()
            return True
        return False

finance_automation = FinanceAutomationService()
