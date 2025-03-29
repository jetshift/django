from jetshift_core.helpers.database import check_database_connection
from jetshift_core.helpers.migrations.common import migrate_supported_pairs
from jetshift_core.helpers.migrations.tables import read_table_schema, migrate_data
from rest_framework import viewsets
from rest_framework.viewsets import ViewSet

from .models import Database, MigrateDatabase, MigrateTable, MigrationTask
from .serializers import DatabaseSerializer, MigrateDatabaseSerializer, MigrateTableSerializer, MigrationTaskSerializer
from .custom_responses import CustomResponseMixin
from .exceptions import BaseValidationError

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from rest_framework.decorators import api_view


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
    queryset = Database.objects.all()
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
    queryset = MigrateDatabase.objects.all()
    serializer_class = MigrateDatabaseSerializer


class MigrateTableViewSet(CustomResponseMixin, viewsets.ModelViewSet):
    serializer_class = MigrateTableSerializer
    queryset = MigrateTable.objects.all()

    def get_queryset(self):
        queryset = MigrateTable.objects.all()
        type_param = self.request.query_params.get('type')
        if type_param:
            queryset = queryset.filter(type=type_param)
        return queryset

    @action(detail=True, methods=['get'], url_path='schema')
    def schema(self, request, pk=None):
        source = {}
        target = {}
        try:
            create_table = request.query_params.get('create', 'true')
            create_table = str(create_table).lower() in ['true', '1', 'yes']
            task_id = request.query_params.get('task_id')
            if not task_id:
                return Response({"success": False, "message": "Task ID not provided"}, status=status.HTTP_400_BAD_REQUEST)

            migrate_table = self.get_object()
            source_database = migrate_table.source_db
            target_database = migrate_table.target_db

            task = MigrationTask.objects.get(id=task_id)

            # Source
            success, message, schema = read_table_schema(database=source_database, table_name=task.source_table, table_type='source')
            source = {
                "success": success,
                "message": message,
                "database": migrate_table.source_db.title,
                "table": task.source_table,
                "schema": schema,
            }

            # Target
            success, message, schema = read_table_schema(database=target_database, table_name=task.target_table, table_type='target', create=create_table, source_db=migrate_table.source_db)
            target = {
                "success": success,
                "message": message,
                "database": migrate_table.target_db.title,
                "table": task.target_table,
                "schema": schema,
            }

            if success:
                return Response({"success": success, "message": message, "source": source, "target": target}, status=status.HTTP_200_OK)
            else:
                return Response({"success": success, "message": message, "source": source, "target": target}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"status": "error", "message": str(e), "source": source, "target": target}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], url_path='sync')
    def migrate(self, request, pk=None):
        try:
            # Task fetching logic
            task_id = request.query_params.get('task_id')
            if task_id:
                migration_task = MigrationTask.objects.get(id=task_id)
            else:
                migration_task = MigrationTask.objects.filter(status="syncing").first() or MigrationTask.objects.filter(status="idle").first()

            if not migration_task:
                return Response({'success': False, 'message': 'No idle task found.'}, status=404)

            migrate_table = self.get_object()
            success, message = migrate_data(migrate_table, migration_task)

            # success, message = True, 'Testing'

            if success:
                return Response({"success": success, "message": message}, status=status.HTTP_200_OK)
            else:
                return Response({"success": success, "message": message}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MigrationTaskSet(viewsets.ModelViewSet):
    queryset = MigrationTask.objects.all()
    serializer_class = MigrationTaskSerializer

    @action(detail=True, methods=['get'], url_path='change-task-status')
    def migrate(self, request, pk=None):
        import asyncio
        from jetshift_core.utils.prefect_api import pause_prefect_deployment

        try:
            # Task fetching logic
            task_status = request.query_params.get('status')
            if not task_status:
                return Response({'success': False, 'message': 'The status param is required'}, status=404)

            migration_task = self.get_object()

            # Update deployment status
            deployment_pause = False if task_status == "syncing" else True
            asyncio.run(pause_prefect_deployment(migration_task.deployment_id, deployment_pause))

            # Update task status
            migration_task.status = task_status
            migration_task.save()

            success, message = True, f"Successfully updated task #{migration_task.id} status to {task_status}"
            if success:
                return Response({"success": success, "message": message}, status=status.HTTP_200_OK)
            else:
                return Response({"success": success, "message": message}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MigrationViewSet(ViewSet):
    serializer_class = MigrateTableSerializer
    queryset = MigrateTable.objects.all()

    @action(detail=False, methods=['get'], url_path='supported-pairs')
    def supported_pairs(self, request):
        pairs = migrate_supported_pairs('', '', check=False)
        return Response(pairs)
