from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from finance.models import Transaction, MonthlySummary, CategoryBudget
from finance.serializers import TransactionSerializer, MonthlySummarySerializer, CategoryBudgetSerializer
from finance.services.accounting import AccountingService


class OwnedQuerysetMixin:
    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


class TransactionViewSet(OwnedQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    queryset = Transaction.objects.all()

    def perform_create(self, serializer):
        tx = AccountingService.create_transaction(user=self.request.user, **serializer.validated_data)
        serializer.instance = tx

    def perform_update(self, serializer):
        tx = self.get_object()
        AccountingService.update_transaction(tx=tx, **serializer.validated_data)

    def perform_destroy(self, instance):
        AccountingService.delete_transaction(tx=instance)


class MonthlySummaryViewSet(OwnedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = MonthlySummarySerializer
    permission_classes = [IsAuthenticated]
    queryset = MonthlySummary.objects.all()


class CategoryBudgetViewSet(OwnedQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = CategoryBudgetSerializer
    permission_classes = [IsAuthenticated]
    queryset = CategoryBudget.objects.all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
