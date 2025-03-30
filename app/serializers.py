from rest_framework import serializers
from .models import Database, MigrateDatabase, MigrateTable, MigrationTask
from django.contrib.auth import authenticate


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(**data)
        if user and user.is_active:
            return user
        raise serializers.ValidationError("Invalid credentials")


class DatabaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Database
        fields = '__all__'


class MigrateDatabaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = MigrateDatabase
        fields = '__all__'


class MigrationTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = MigrationTask
        fields = '__all__'


class MigrateTableSerializer(serializers.ModelSerializer):
    source_database = serializers.SerializerMethodField()
    target_database = serializers.SerializerMethodField()
    tasks = MigrationTaskSerializer(many=True, read_only=True)

    class Meta:
        model = MigrateTable
        fields = '__all__'
        extra_fields = ['tasks']

    def get_source_database(self, obj):
        if obj.source_db:
            return {
                "id": obj.source_db.id,
                "title": obj.source_db.title
            }
        return None

    def get_target_database(self, obj):
        if obj.target_db:
            return {
                "id": obj.target_db.id,
                "title": obj.target_db.title
            }
        return None
