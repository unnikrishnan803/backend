from rest_framework import serializers

from .models import Player, Question, Room, Round, SyncResult


class CreateRoomSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=32)


class JoinRoomSerializer(serializers.Serializer):
    room_code = serializers.CharField(max_length=6)
    name = serializers.CharField(max_length=32)


class StartRoundSerializer(serializers.Serializer):
    room_code = serializers.CharField(max_length=6)
    question_id = serializers.IntegerField(required=False)


class SubmitAnswerSerializer(serializers.Serializer):
    room_code = serializers.CharField(max_length=6)
    player_id = serializers.UUIDField()
    text = serializers.CharField(max_length=1000)


class SubmitGuessSerializer(serializers.Serializer):
    room_code = serializers.CharField(max_length=6)
    player_id = serializers.UUIDField()
    answer_id = serializers.IntegerField()
    guessed_player_id = serializers.UUIDField()


class PlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = ["id", "name", "score", "is_host", "is_connected", "joined_at"]


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ["id", "text", "type"]


class RoundSerializer(serializers.ModelSerializer):
    question = QuestionSerializer()

    class Meta:
        model = Round
        fields = ["id", "number", "question", "started_at", "ended_at"]


class RoomSerializer(serializers.ModelSerializer):
    players = PlayerSerializer(many=True)
    active_question = QuestionSerializer()

    class Meta:
        model = Room
        fields = [
            "id",
            "code",
            "status",
            "current_round",
            "max_rounds",
            "active_question",
            "players",
        ]


class SyncResultSerializer(serializers.ModelSerializer):
    player_one_name = serializers.CharField(source="player_one.name")
    player_two_name = serializers.CharField(source="player_two.name")

    class Meta:
        model = SyncResult
        fields = [
            "player_one",
            "player_two",
            "player_one_name",
            "player_two_name",
            "answer_similarity",
            "correct_guess_rate",
            "mutual_selection_rate",
            "sync_percentage",
        ]
