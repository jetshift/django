from rest_framework import viewsets
from .models import Database, MigrateDatabase, MigrateTable
from .serializers import DatabaseSerializer, MigrateDatabaseSerializer, MigrateTableSerializer
from .custom_responses import CustomResponseMixin
from .exceptions import BaseValidationError


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


class MigrateDatabaseViewSet(CustomResponseMixin, viewsets.ModelViewSet):
    queryset = MigrateDatabase.objects.all()
    serializer_class = MigrateDatabaseSerializer


class MigrateTableViewSet(CustomResponseMixin, viewsets.ModelViewSet):
    queryset = MigrateTable.objects.all()
    serializer_class = MigrateTableSerializer
