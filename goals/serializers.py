from rest_framework import serializers
from goals.models import Goal


class GoalSerializer(serializers.ModelSerializer):
    current_saved = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    progress_percent = serializers.IntegerField(read_only=True)

    class Meta:
        model = Goal
        fields = [
            'id',
            'title',
            'description',
            'target_amount',
            'target_date',
            'status',
            'created_at',
            'updated_at',
            'current_saved',
            'progress_percent',
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at', 'current_saved', 'progress_percent']

    def validate_target_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Target amount must be greater than 0')
        return value

    def validate_target_date(self, value):
        from django.utils import timezone

        if value <= timezone.now().date():
            raise serializers.ValidationError('Target date must be in the future')
        return value
