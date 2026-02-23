from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def room_group_name(room_code: str) -> str:
    return f"room_{room_code.upper()}"


def broadcast_room_event(room_code: str, event: str, payload: dict) -> None:
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        room_group_name(room_code),
        {
            "type": "game.event",
            "event": event,
            "payload": payload,
        },
    )
