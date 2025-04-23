from django.contrib.auth.models import User
from rest_framework import viewsets
from app.custom_responses import CustomResponseMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers
from app.permissions import IsSuperUser


class UserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = [
            'id', 'name', 'first_name', 'last_name',
            'username', 'email', 'password',
            'is_superuser', 'is_active', 'date_joined'
        ]

    def get_name(self, obj):
        return obj.get_full_name()

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserViewSet(CustomResponseMixin, viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated & IsSuperUser]
