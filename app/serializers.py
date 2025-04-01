from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from app.models import Database, MigrateDatabase, MigrateTable, MigrationTask
from django.contrib.auth import authenticate, get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        username_or_email = attrs.get("username")
        password = attrs.get("password")

        user = authenticate(request=self.context.get('request'), username=username_or_email, password=password)

        if user is None:
            try:
                user_obj = User.objects.get(email__iexact=username_or_email)
                user = authenticate(request=self.context.get('request'), username=user_obj.username, password=password)
            except User.DoesNotExist:
                raise serializers.ValidationError(_("No user found with this email"))

        if user is None:
            raise serializers.ValidationError(_("Incorrect credentials"))

        if not user.is_active:
            raise serializers.ValidationError(_("User account is disabled"))

        self.user = user

        # ✅ Use get_token to include custom claims
        refresh = self.get_token(user)

        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.username
        token["email"] = user.email
        token["name"] = user.get_full_name()

        return token


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
