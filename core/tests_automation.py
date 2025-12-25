from django.test import TestCase
from django.contrib.auth.models import User
from core.models import Income, Expense, UserGoal
from core.services.finance_automation import finance_automation
import datetime

class FinanceAutomationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testteen', password='password')

    def test_parse_raw_text(self):
        """Test that the parser can extract data from messy strings."""
        raw_text = "01.12 Magnit 450r\n02.12 Yandex 320.50 сом; 500 Gift"
        results = finance_automation.parse_raw_text(raw_text)
        
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]['amount'], 450.0)
        self.assertEqual(results[1]['amount'], 320.50)
        self.assertEqual(results[0]['description'].lower(), 'magnit')
        self.assertEqual(results[2]['amount'], 500.0)

    def test_fallback_categorization(self):
        """Test rule-based classification when AI is off."""
        data = [
            {'description': 'KFC Burger', 'amount': 400},
            {'description': 'Uber ride', 'amount': 150}
        ]
        results = finance_automation.fallback_categorization(data)
        self.assertEqual(results[0]['category'], 'food')
        self.assertEqual(results[1]['category'], 'transport')

    def test_money_leaks_logic(self):
        """Test that analytics correctly sums categories."""
        Expense.objects.create(user=self.user, amount=100, date=datetime.date.today(), expense_type='food')
        Expense.objects.create(user=self.user, amount=200, date=datetime.date.today(), expense_type='food')
        Expense.objects.create(user=self.user, amount=50, date=datetime.date.today(), expense_type='transport')
        
        leaks = finance_automation.get_money_leaks(self.user)
        self.assertEqual(leaks[0]['expense_type'], 'food')
        self.assertEqual(leaks[0]['total'], 300)
