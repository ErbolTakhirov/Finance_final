from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from goals.models import Goal
from goals.serializers import GoalSerializer
from goals.services import GoalService


class GoalViewSet(viewsets.ModelViewSet):
    serializer_class = GoalSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        goal = GoalService.create_goal(user=self.request.user, **serializer.validated_data)
        serializer.instance = goal

    def perform_update(self, serializer):
        goal = self.get_object()
        GoalService.update_goal(goal, **serializer.validated_data)

    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        goal = self.get_object()
        progress = GoalService.calculate_progress(goal)
        return Response({
            'current_saved': str(progress.current_saved),
            'progress_percent': progress.progress_percent,
            'projected_date': progress.projected_date.isoformat() if progress.projected_date else None,
            'probability_of_success': progress.probability_of_success,
        })

    @action(detail=False, methods=['post'])
    def update_statuses(self, request):
        updated = GoalService.auto_update_statuses(request.user)
        return Response({'updated': updated}, status=status.HTTP_200_OK)
