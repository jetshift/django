from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from app.serializers import CustomTokenObtainPairSerializer
from dotenv import load_dotenv
from rest_framework import status
from rest_framework.response import Response
from app.views.user_views import UserSerializer

load_dotenv()


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class ProtectedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user_data = UserSerializer(request.user).data
            return Response(user_data)
        except Exception as e:
            return Response(
                {"error": "Something went wrong.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
