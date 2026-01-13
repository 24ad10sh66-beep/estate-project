from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

def send_notification_to_group(group, payload):
    """Send a notification payload to a channel group (WebSocket)"""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        group,
        {
            "type": "send_notification",
            "payload": payload,
        }
    )

# Example usage:
# send_notification_to_group("seller_42", {"msg": "New booking!"})
