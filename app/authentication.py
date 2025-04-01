from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework.exceptions import AuthenticationFailed as DRFAuthFailed


class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        # Read token from cookie
        token = request.COOKIES.get('auth_token')

        if not token:
            return None  # Return None so other authenticators can try

        try:
            validated_token = self.get_validated_token(token)
            return self.get_user(validated_token), validated_token
        except InvalidToken as e:
            raise DRFAuthFailed('Invalid token in cookie') from e
