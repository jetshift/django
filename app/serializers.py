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
    source = serializers.SerializerMethodField()
    target = serializers.SerializerMethodField()

    class Meta:
        model = MigrateTable
        fields = '__all__'
        extra_fields = ['source_db_title', 'target_db_title']

    def get_source(self, obj):
        if obj.source_db:
            return {
                "id": obj.source_db.id,
                "title": obj.source_db.title
            }
        return None

    def get_target(self, obj):
        if obj.target_db:
            return {
                "id": obj.target_db.id,
                "title": obj.target_db.title
            }
        return None
