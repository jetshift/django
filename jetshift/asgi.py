import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from app.utils.consumers import JetSshitWebSocketConsumer
from django.urls import path
from dotenv import load_dotenv

load_dotenv()

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jetshift.settings')

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": URLRouter([
            path("ws/", JetSshitWebSocketConsumer.as_asgi()),
        ]),
    }
)
