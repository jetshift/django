from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from app.custom_responses import CustomResponseMixin
from app.exceptions import BaseValidationError
from app.models import JSDatabase, JSMigrateDatabase, JSTask
from app.serializers import DatabaseSerializer, MigrateDatabaseSerializer, MigrateTableSerializer
from jetshift_core.helpers.database import check_database_connection
from jetshift_core.helpers.migrations.common import migrate_supported_pairs


@api_view(['GET'])
def test_view(request):
    # Send WebSocket notification
    from app.utils.notify import trigger_websocket_notification
    trigger_websocket_notification({
        "task_id": 1,
        "total_source_items": 1,
        "total_target_items": 1
    })

    return Response({'message': 'Test route is working!'})


class DatabaseViewSet(CustomResponseMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = JSDatabase.objects.all()
    serializer_class = DatabaseSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        db_type = self.request.query_params.get('type', None)

        if db_type:
            if db_type not in ['source', 'target']:
                raise BaseValidationError(f"Invalid 'type' parameter: {db_type}")

            queryset = queryset.filter(type=db_type)

        return queryset

    @action(detail=True, methods=['get'], url_path='check-connection')
    def check_connection(self, request, pk=None):
        try:
            database = self.get_object()
            success, message = check_database_connection(database)

            if success:
                return Response({"success": success, "message": message}, status=status.HTTP_200_OK)
            else:
                return Response({"success": success, "message": message}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MigrateDatabaseViewSet(CustomResponseMixin, viewsets.ModelViewSet):
    queryset = JSMigrateDatabase.objects.all()
    serializer_class = MigrateDatabaseSerializer


class MigrationViewSet(ViewSet):
    serializer_class = MigrateTableSerializer
    queryset = JSTask.objects.all()

    @action(detail=False, methods=['get'], url_path='supported-pairs')
    def supported_pairs(self, request):
        pairs = migrate_supported_pairs('', '', check=False)
        return Response(pairs)
