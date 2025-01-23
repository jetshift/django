import json
from channels.generic.websocket import AsyncWebsocketConsumer


class MyWebSocketConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Accept the WebSocket connection
        await self.accept()
        await self.send(json.dumps({"message": "WebSocket connection established!"}))

    async def disconnect(self, close_code):
        # Handle WebSocket disconnection
        print(f"WebSocket disconnected: {close_code}")

    async def receive(self, text_data):
        # Handle messages received from the client
        data = json.loads(text_data)
        await self.send(json.dumps({
            "message": f"Message received: {data.get('message', '')}"
        }))
