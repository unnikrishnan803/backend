from django.urls import path

from .views import (
    CreateRoomView,
    FinishRoomView,
    JoinRoomView,
    RevealAnswerView,
    RoomStateView,
    StartRoundView,
    SubmitAnswerView,
    SubmitGuessView,
)

urlpatterns = [
    path("rooms/create/", CreateRoomView.as_view(), name="create-room"),
    path("rooms/join/", JoinRoomView.as_view(), name="join-room"),
    path("rooms/<str:room_code>/state/", RoomStateView.as_view(), name="room-state"),
    path("rooms/start-round/", StartRoundView.as_view(), name="start-round"),
    path("rooms/<str:room_code>/reveal/", RevealAnswerView.as_view(), name="reveal-answer"),
    path("rooms/submit-answer/", SubmitAnswerView.as_view(), name="submit-answer"),
    path("rooms/submit-guess/", SubmitGuessView.as_view(), name="submit-guess"),
    path("rooms/<str:room_code>/finish/", FinishRoomView.as_view(), name="finish-room"),
]
