from rest_framework.routers import DefaultRouter
from finance.views import TransactionViewSet, MonthlySummaryViewSet, CategoryBudgetViewSet

router = DefaultRouter()
router.register('transactions', TransactionViewSet, basename='transaction')
router.register('monthly-summaries', MonthlySummaryViewSet, basename='monthly-summary')
router.register('category-budgets', CategoryBudgetViewSet, basename='category-budget')

urlpatterns = router.urls
