import os
import json
import requests
from channels.generic.websocket import AsyncWebsocketConsumer

class AzureBotConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.conversation_id = os.getenv("AZURE_BOT_CONVERSATION_ID")
        self.direct_line_secret = os.getenv("AZURE_DIRECT_LINE_SECRET")
        self.endpoint = os.getenv("AZURE_BOT_ENDPOINT", "https://directline.botframework.com/v3/directline")

    async def receive(self, text_data):
        data = json.loads(text_data)
        user_message = data.get("message")
        # Send message to Azure Bot via Direct Line REST API
        url = f"{self.endpoint}/conversations/{self.conversation_id}/activities"
        headers = {"Authorization": f"Bearer {self.direct_line_secret}", "Content-Type": "application/json"}
        payload = {
            "type": "message",
            "from": {"id": "django-user"},
            "text": user_message
        }
        response = requests.post(url, headers=headers, json=payload)
        bot_reply = "No reply"
        if response.ok:
            res_json = response.json()
            # Try to get bot reply from activities (Direct Line returns activityId, not reply)
            # For demo, just echo user message
            bot_reply = res_json.get("id", "Message sent")
        await self.send(text_data=json.dumps({"reply": bot_reply}))
