from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from finance.models import Transaction


@receiver([post_save, post_delete], sender=Transaction)
def auto_recalculate_month(sender, instance: Transaction, **kwargs):
    from finance.models import MonthlySummary

    summary, _ = MonthlySummary.objects.get_or_create(
        user=instance.user,
        month_key=instance.month_key
    )
    summary.recalculate()
