from rest_framework import viewsets, serializers
from rest_framework.viewsets import ViewSet

from .models import Database, MigrateDatabase, MigrateTable
from .serializers import DatabaseSerializer, MigrateDatabaseSerializer, MigrateTableSerializer
from .custom_responses import CustomResponseMixin
from .exceptions import BaseValidationError

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status


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
        from app.services.database import check_database_connection

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
    queryset = MigrateTable.objects.all()
    serializer_class = MigrateTableSerializer

    @action(detail=True, methods=['get'], url_path='schema')
    def schema(self, request, pk=None):
        from app.services.migrate_tables import read_table_schema

        try:
            # Accessing the query parameter
            table = request.query_params.get('table')
            table_type = request.query_params.get('type', 'source')

            migrate_table = self.get_object()
            success, message, schema = read_table_schema(migrate_table, table_type=table_type, table_name=table)

            if success:
                return Response({"success": success, "message": message, "schema": schema}, status=status.HTTP_200_OK)
            else:
                return Response({"success": success, "message": message}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], url_path='migrate')
    def migrate(self, request, pk=None):
        from app.services.migrate_tables import migrate_data

        try:
            # Accessing the query parameter
            table = request.query_params.get('table', 'users')

            migrate_table = self.get_object()
            success, message = migrate_data(migrate_table, table)

            if success:
                return Response({"success": success, "message": message}, status=status.HTTP_200_OK)
            else:
                return Response({"success": success, "message": message}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MigrationViewSet(ViewSet):
    @action(detail=False, methods=['get'], url_path='supported-pairs')
    def supported_pairs(self, request):
        from .services.migrate.common import migrate_supported_pairs
        pairs = migrate_supported_pairs('', '', check=False)
        return Response(pairs)
