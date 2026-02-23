from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .engine import broadcast_room_event
from .models import Room
from .serializers import (
    CreateRoomSerializer,
    JoinRoomSerializer,
    StartRoundSerializer,
    SubmitAnswerSerializer,
    SubmitGuessSerializer,
    SyncResultSerializer,
)
from .services import (
    GameServiceError,
    calculate_sync_results,
    create_room_with_host,
    get_room_snapshot,
    join_room,
    reveal_random_answer,
    start_round,
    submit_answer,
    submit_guess,
)


def _service_error_response(exc: GameServiceError) -> Response:
    return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class CreateRoomView(APIView):
    def post(self, request):
        serializer = CreateRoomSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            room, host = create_room_with_host(serializer.validated_data["name"])
        except GameServiceError as exc:
            return _service_error_response(exc)

        payload = get_room_snapshot(room)
        payload["player_id"] = str(host.id)
        payload["player_name"] = host.name
        return Response(payload, status=status.HTTP_201_CREATED)


class JoinRoomView(APIView):
    def post(self, request):
        serializer = JoinRoomSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            room, player = join_room(
                code=serializer.validated_data["room_code"],
                name=serializer.validated_data["name"],
            )
        except GameServiceError as exc:
            return _service_error_response(exc)

        payload = get_room_snapshot(room)
        payload["player_id"] = str(player.id)
        payload["player_name"] = player.name
        broadcast_room_event(room.code, "state_updated", payload)
        return Response(payload, status=status.HTTP_200_OK)


class RoomStateView(APIView):
    def get(self, request, room_code: str):
        room = get_object_or_404(Room, code=room_code.upper())
        return Response(get_room_snapshot(room))


class StartRoundView(APIView):
    def post(self, request):
        serializer = StartRoundSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            room, _ = start_round(
                room_code=serializer.validated_data["room_code"].upper(),
                question_id=serializer.validated_data.get("question_id"),
            )
        except GameServiceError as exc:
            return _service_error_response(exc)

        payload = get_room_snapshot(room)
        broadcast_room_event(room.code, "state_updated", payload)
        return Response(payload)


class SubmitAnswerView(APIView):
    def post(self, request):
        serializer = SubmitAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            room, _, answer = submit_answer(
                room_code=serializer.validated_data["room_code"].upper(),
                player_id=str(serializer.validated_data["player_id"]),
                text=serializer.validated_data["text"],
            )
        except GameServiceError as exc:
            return _service_error_response(exc)

        payload = get_room_snapshot(room)
        payload["last_answer_id"] = answer.id
        broadcast_room_event(room.code, "state_updated", payload)
        return Response(payload)


class RevealAnswerView(APIView):
    def post(self, request, room_code: str):
        try:
            room, _, revealed = reveal_random_answer(room_code=room_code.upper())
        except GameServiceError as exc:
            return _service_error_response(exc)

        payload = get_room_snapshot(room)
        payload["revealed_answer_id"] = revealed.id
        payload["revealed_answer_text"] = revealed.text
        broadcast_room_event(room.code, "state_updated", payload)
        return Response(payload)


class SubmitGuessView(APIView):
    def post(self, request):
        serializer = SubmitGuessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            room, _, guess, reveal_complete = submit_guess(
                room_code=serializer.validated_data["room_code"].upper(),
                player_id=str(serializer.validated_data["player_id"]),
                answer_id=serializer.validated_data["answer_id"],
                guessed_player_id=str(serializer.validated_data["guessed_player_id"]),
            )
        except GameServiceError as exc:
            return _service_error_response(exc)

        payload = get_room_snapshot(room)
        payload["guess"] = {
            "id": guess.id,
            "is_correct": guess.is_correct,
            "points_awarded": guess.points_awarded,
        }
        payload["reveal_complete"] = reveal_complete
        broadcast_room_event(room.code, "state_updated", payload)
        return Response(payload)


class FinishRoomView(APIView):
    def post(self, request, room_code: str):
        try:
            calculate_sync_results(room_code.upper())
        except GameServiceError as exc:
            return _service_error_response(exc)

        room = get_object_or_404(Room, code=room_code.upper())
        payload = get_room_snapshot(room)
        payload["pairs"] = SyncResultSerializer(room.sync_results.order_by("-sync_percentage"), many=True).data
        broadcast_room_event(room.code, "final_results", payload)
        return Response(payload)
