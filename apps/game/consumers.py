from __future__ import annotations

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .models import Room, SyncResult
from .serializers import SyncResultSerializer
from .services import (
    GameServiceError,
    calculate_sync_results,
    get_room_snapshot,
    reveal_random_answer,
    start_round,
    submit_answer,
    submit_guess,
)


def room_group_name(room_code: str) -> str:
    return f"room_{room_code.upper()}"


class GameConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.room_code = self.scope["url_route"]["kwargs"]["room_code"].upper()
        self.group_name = room_group_name(self.room_code)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({"event": "connected", "payload": {"room_code": self.room_code}})
        await self._send_snapshot()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        action = content.get("action")
        data = content.get("data", {})
        try:
            if action == "sync_state":
                await self._send_snapshot()
            elif action == "start_round":
                await self._start_round(data)
            elif action == "submit_answer":
                await self._submit_answer(data)
            elif action == "reveal_answer":
                await self._reveal_answer()
            elif action == "submit_guess":
                await self._submit_guess(data)
            elif action == "finish_room":
                await self._finish_room()
            else:
                await self.send_json({"event": "error", "payload": {"message": "Unsupported action"}})
        except GameServiceError as exc:
            await self.send_json({"event": "error", "payload": {"message": str(exc)}})

    async def game_event(self, event):
        await self.send_json({"event": event["event"], "payload": event["payload"]})

    async def _broadcast_state(self):
        snapshot = await self._get_snapshot()
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "game.event",
                "event": "state_updated",
                "payload": snapshot,
            },
        )

    async def _send_snapshot(self):
        snapshot = await self._get_snapshot()
        await self.send_json({"event": "state_updated", "payload": snapshot})

    async def _start_round(self, data: dict):
        question_id = data.get("question_id")
        await self._start_round_db(question_id)
        await self._broadcast_state()

    async def _submit_answer(self, data: dict):
        await self._submit_answer_db(data["player_id"], data["text"])
        await self._broadcast_state()

    async def _reveal_answer(self):
        await self._reveal_answer_db()
        await self._broadcast_state()

    async def _submit_guess(self, data: dict):
        reveal_complete = await self._submit_guess_db(
            data["player_id"],
            int(data["answer_id"]),
            data["guessed_player_id"],
        )
        await self._broadcast_state()
        if reveal_complete:
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "game.event",
                    "event": "round_reveal_completed",
                    "payload": {"room_code": self.room_code},
                },
            )

    async def _finish_room(self):
        await self._finish_room_db()
        results = await self._sync_results()
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "game.event",
                "event": "final_results",
                "payload": {"pairs": results},
            },
        )
        await self._broadcast_state()

    @database_sync_to_async
    def _get_snapshot(self) -> dict:
        room = Room.objects.get(code=self.room_code)
        return get_room_snapshot(room)

    @database_sync_to_async
    def _start_round_db(self, question_id):
        start_round(self.room_code, question_id=question_id)

    @database_sync_to_async
    def _submit_answer_db(self, player_id: str, text: str):
        submit_answer(self.room_code, player_id=player_id, text=text)

    @database_sync_to_async
    def _reveal_answer_db(self):
        reveal_random_answer(self.room_code)

    @database_sync_to_async
    def _submit_guess_db(self, player_id: str, answer_id: int, guessed_player_id: str) -> bool:
        _, _, _, reveal_complete = submit_guess(
            room_code=self.room_code,
            player_id=player_id,
            answer_id=answer_id,
            guessed_player_id=guessed_player_id,
        )
        return reveal_complete

    @database_sync_to_async
    def _finish_room_db(self):
        calculate_sync_results(self.room_code)

    @database_sync_to_async
    def _sync_results(self):
        room = Room.objects.get(code=self.room_code)
        results = SyncResult.objects.filter(room=room).order_by("-sync_percentage")
        return SyncResultSerializer(results, many=True).data
