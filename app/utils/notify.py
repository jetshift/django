import os
import django
import asyncio
from channels.layers import get_channel_layer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jetshift.settings')
django.setup()


async def send_ws_message(message):
    channel_layer = get_channel_layer()
    if not channel_layer:
        print("Channel layer is None. Check setup.")
        return

    await channel_layer.group_send(
        'jetshift',
        {
            'type': 'websocket_message',
            'message': message
        }
    )


def trigger_websocket_notification(message):
    asyncio.run(send_ws_message(message))


async def trigger_websocket_notification_async(message):
    await send_ws_message(message)
