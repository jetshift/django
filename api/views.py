from rest_framework import viewsets
from .models import User, Database, MigrateDatabase, MigrateTable
from .serializers import UserSerializer, DatabaseSerializer, MigrateDatabaseSerializer, MigrateTableSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class DatabaseViewSet(viewsets.ModelViewSet):
    queryset = Database.objects.all()
    serializer_class = DatabaseSerializer


class MigrateDatabaseViewSet(viewsets.ModelViewSet):
    queryset = MigrateDatabase.objects.all()
    serializer_class = MigrateDatabaseSerializer


class MigrateTableViewSet(viewsets.ModelViewSet):
    queryset = MigrateTable.objects.all()
    serializer_class = MigrateTableSerializer
