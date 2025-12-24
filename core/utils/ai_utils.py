import json
import re
from typing import List, Dict, Optional, Tuple
from django.db.models import Sum
from core.llm import chat_with_context
from core.models import Income, Expense

def ai_categorize_batch(transactions: List[Dict], type_name: str) -> List[str]:
    """
    Categorizes a batch of transactions using LLM.
    transactions: list of dicts with 'description' and possibly 'amount'
    type_name: 'income' or 'expense'
    """
    if not transactions:
        return []

    if type_name == 'income':
        choices = dict(Income._meta.get_field('income_type').choices)
    else:
        choices = dict(Expense._meta.get_field('expense_type').choices)

    choices_str = "\n".join([f"- {k}: {v}" for k, v in choices.items()])
    
    # Prepare prompt
    items_to_categorize = []
    for i, t in enumerate(transactions):
        desc = t.get('description', '') or t.get('category', '') or 'No description'
        items_to_categorize.append(f"ID {i}: {desc}")
    
    items_to_categorize_str = "\n".join(items_to_categorize)
    prompt = f"""
    You are a financial assistant. Categorize the following {type_name} transactions into the given categories.
    
    Target Categories:
    {choices_str}
    
    Transactions:
    {items_to_categorize_str}
    
    Return ONLY a JSON object where keys are the IDs from the list and values are the internal category keys (e.g., 'rent', 'food').
    Example: {{"0": "rent", "1": "food"}}
    """
    
    try:
        response = chat_with_context(
            messages=[{'role': 'user', 'content': prompt}],
            user_data="",
            system_instruction="You are a JSON-only response bot. Provide only the mapping from ID to category key.",
            anonymize=True
        )
        
        # Extract JSON
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            mapping = json.loads(match.group(0))
            result = []
            for i in range(len(transactions)):
                cat = mapping.get(str(i))
                if cat in choices:
                    result.append(cat)
                else:
                    result.append('other')
            return result
    except Exception as e:
        print(f"AI Categorization error: {e}")
    
    return ['other'] * len(transactions)

def ai_predict_next_month(user, incomes_qs, expenses_qs) -> Dict:
    """
    Uses LLM to predict next month profit based on historical data trajectory.
    """
    # Prepare context: 
    # Aggregate by month for the last 6 months
    from django.db.models.functions import TruncMonth
    
    monthly_data = {}
    
    inc_by_month = incomes_qs.annotate(month=TruncMonth('date')).values('month').annotate(total=Sum('amount')).order_by('month')
    exp_by_month = expenses_qs.annotate(month=TruncMonth('date')).values('month').annotate(total=Sum('amount')).order_by('month')
    
    for row in inc_by_month:
        m = row['month'].strftime('%Y-%m')
        if m not in monthly_data: monthly_data[m] = {'income': 0, 'expense': 0}
        monthly_data[m]['income'] = float(row['total'])
        
    for row in exp_by_month:
        m = row['month'].strftime('%Y-%m')
        if m not in monthly_data: monthly_data[m] = {'income': 0, 'expense': 0}
        monthly_data[m]['expense'] = float(row['total'])
        
    history_str = "\n".join([f"{m}: Income {d['income']}, Expense {d['expense']}, Profit {d['income'] - d['expense']}" for m, d in sorted(monthly_data.items())])
    
    prompt = f"""
    Based on the following historical financial data of a user, predict their profit for the next month.
    
    Historical Data (by month):
    {history_str}
    
    Rules:
    - Consider the trend (growing or declining).
    - If data is sparse, be conservative.
    - Return ONLY a JSON object with 'next_month_profit_prediction' (float) and a short 'reasoning' (string).
    
    Example: {{"next_month_profit_prediction": 1250.50, "reasoning": "Based on a 10% upward trend in income and stable expenses."}}
    """
    
    try:
        response = chat_with_context(
            messages=[{'role': 'user', 'content': prompt}],
            user_data=history_str,
            system_instruction="You are a financial prediction engine. Provide JSON output.",
            anonymize=True,
            user=user
        )
        
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            return data
    except Exception as e:
        print(f"AI Prediction error: {e}")
        
    return {"next_month_profit_prediction": 0.0, "reasoning": "Недостаточно данных для ИИ-прогноза."}
