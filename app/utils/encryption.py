import base64
import hashlib
from cryptography.fernet import Fernet
from django.conf import settings


def get_fernet():
    # Derive a 32-byte key from Django's SECRET_KEY using SHA256, then base64 encode it
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key)
    return Fernet(fernet_key)
