import json
from channels.generic.websocket import AsyncWebsocketConsumer


class JetSshitWebSocketConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = 'jetshift'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send(json.dumps({"message": "WebSocket connection established!"}))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        print(f"WebSocket disconnected: {close_code}")

    async def receive(self, text_data):
        data = json.loads(text_data)
        await self.send(json.dumps({
            "message": f"{data.get('message', '')}"
        }))

    async def websocket_message(self, event):
        await self.send(text_data=json.dumps({"message": event['message']}))
