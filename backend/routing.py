from django.urls import re_path
from .consumers import AzureBotConsumer

websocket_urlpatterns = [
    re_path(r'ws/bot/$', AzureBotConsumer.as_asgi()),
]
