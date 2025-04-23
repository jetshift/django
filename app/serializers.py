from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from app.models import JSDatabase, JSMigrateDatabase, JSTask, JSSubTask
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

        # Use get_token to include custom claims
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
        token["is_superuser"] = user.is_superuser
        token["name"] = user.get_full_name()

        return token


class DatabaseSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = JSDatabase
        fields = '__all__'

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        instance = super().create(validated_data)
        if password:
            instance.password = password  # Triggers model encryption
            instance.save()
        return instance

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        instance = super().update(instance, validated_data)
        if password:
            instance.password = password
            instance.save()
        return instance


class JSMigrateDatabaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = JSMigrateDatabase
        fields = '__all__'


class JSSubTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = JSSubTask
        fields = '__all__'


class JSTaskSerializer(serializers.ModelSerializer):
    source_database = serializers.SerializerMethodField()
    target_database = serializers.SerializerMethodField()
    subtasks = serializers.SerializerMethodField()

    class Meta:
        model = JSTask
        fields = '__all__'
        extra_fields = ['subtasks']

    def get_source_database(self, obj):
        if obj.source_db:
            return {"id": obj.source_db.id, "title": obj.source_db.title}
        return None

    def get_target_database(self, obj):
        if obj.target_db:
            return {"id": obj.target_db.id, "title": obj.target_db.title}
        return None

    def get_subtasks(self, obj):
        ordered_subtasks = obj.subtasks.all().order_by('-id')
        return JSSubTaskSerializer(ordered_subtasks, many=True).data
