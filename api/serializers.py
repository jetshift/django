from rest_framework import serializers
from .models import User, Database, MigrateDatabase, MigrateTable


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'  # Include all fields or specify: ['id', 'name', 'username', 'email']


class DatabaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Database
        fields = '__all__'


class MigrateDatabaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = MigrateDatabase
        fields = '__all__'


class MigrateTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = MigrateTable
        fields = '__all__'
