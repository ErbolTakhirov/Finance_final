from rest_framework import serializers
from finance.models import Transaction, MonthlySummary, CategoryBudget


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = [
            'id',
            'date',
            'amount',
            'type',
            'category',
            'description',
            'source',
            'is_verified',
            'month_key',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'month_key', 'created_at', 'updated_at']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Amount must be greater than 0')
        return value


class MonthlySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = MonthlySummary
        fields = [
            'id',
            'month_key',
            'total_income',
            'total_expense',
            'profit',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'total_income', 'total_expense', 'profit', 'created_at', 'updated_at']


class CategoryBudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryBudget
        fields = [
            'id',
            'category',
            'monthly_limit',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
