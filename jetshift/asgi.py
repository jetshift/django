import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path
from core.consumers import MyWebSocketConsumer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jetshift.settings')

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": URLRouter([
            path("ws/", MyWebSocketConsumer.as_asgi()),
        ]),
    }
)
