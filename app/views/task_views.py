from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action

from app.custom_responses import CustomResponseMixin
from app.models import JSTask, JSSubTask, default_sub_task_config
from app.serializers import JSTaskSerializer, JSSubTaskSerializer
from app.utils.model import normalize_config_types
from jetshift_core.helpers.migrations.tables import read_table_schema, migrate_data


class TaskViewSet(CustomResponseMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = JSTaskSerializer
    queryset = JSTask.objects.all().order_by('-id')

    def get_queryset(self):
        queryset = JSTask.objects.all().order_by('-id')
        type_param = self.request.query_params.get('type')
        if type_param:
            queryset = queryset.filter(type=type_param)
        return queryset

    @action(detail=True, methods=['get'], url_path='schema')
    def schema(self, request, pk=None):
        success = True
        message = "Schema fetched successfully"
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

            task = JSSubTask.objects.get(id=task_id)

            # Source
            success_source, message_source, schema_source = read_table_schema(database=source_database, task=task, table_type='source')
            source = {
                "success": success_source,
                "message": message_source,
                "database": migrate_table.source_db.title,
                "table": task.source_table,
                "schema": schema_source,
            }

            # Target
            success_target, message_target, schema_target = read_table_schema(database=target_database, task=task, table_type='target', create=create_table, source_db=migrate_table.source_db)
            target = {
                "success": success_target,
                "message": message_target,
                "database": migrate_table.target_db.title,
                "table": task.target_table,
                "schema": schema_target,
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
                subtask = JSSubTask.objects.get(id=task_id)
            else:
                subtask = JSSubTask.objects.filter(status="syncing").first() or JSSubTask.objects.filter(status="idle").first()

            if not subtask:
                return Response({'success': False, 'message': 'No idle task found.'}, status=404)

            migrate_table = self.get_object()
            success, message = migrate_data(migrate_table, subtask)

            # success, message = True, 'Testing'

            if success:
                return Response({"success": success, "message": message}, status=status.HTTP_200_OK)
            else:
                return Response({"success": success, "message": message}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SubTaskViewSet(CustomResponseMixin, viewsets.ModelViewSet):
    queryset = JSSubTask.objects.all().order_by('-id')
    serializer_class = JSSubTaskSerializer

    def create(self, request, *args, **kwargs):
        data = request.data.copy()

        # Merge user config with defaults
        user_config = data.get('config', {})
        if isinstance(user_config, str):
            import json
            user_config = json.loads(user_config)

        user_config = normalize_config_types(user_config)
        merged_config = {**default_sub_task_config(), **user_config}
        data['config'] = merged_config

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        return self._custom_response(
            data=serializer.data,
            message='Subtask created successfully.',
            success=True,
            status_code=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()

        data = request.data.copy()

        # Only merge config if it is provided
        if 'config' in data:
            user_config = data['config']
            if isinstance(user_config, str):
                import json
                user_config = json.loads(user_config)

            user_config = normalize_config_types(user_config)
            merged_config = {**default_sub_task_config(), **user_config}
            data['config'] = merged_config

        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated_instance = serializer.save()

        return self._custom_response(
            data=serializer.data,
            message='Subtask updated successfully.',
            success=True,
            status_code=status.HTTP_200_OK
        )

    @action(detail=True, methods=['get'], url_path='change-task-status')
    def change_task_status(self, request, pk=None):
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

    @action(detail=True, methods=['get'], url_path='cdc')
    def cdc(self, request, pk=None):
        from jetshift_core.tasks.cdc_from_aws_s3 import cdc_from_s3_csv_flow_deploy

        try:
            subtask = self.get_object()
            success, message = cdc_from_s3_csv_flow_deploy(subtask)

            # success, message = True, 'Testing'

            if success:
                return Response({"success": success, "message": message}, status=status.HTTP_200_OK)
            else:
                return Response({"success": success, "message": message}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
