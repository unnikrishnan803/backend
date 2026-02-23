from __future__ import annotations

import uuid

from django.db import models


class RoomStatus(models.TextChoices):
    LOBBY = "LOBBY", "Lobby"
    QUESTION = "QUESTION", "Question"
    REVEAL = "REVEAL", "Reveal"
    SCOREBOARD = "SCOREBOARD", "Scoreboard"
    FINISHED = "FINISHED", "Finished"


class QuestionType(models.TextChoices):
    FUNNY = "FUNNY", "Funny"
    LIFE = "LIFE", "Life"
    ROMANCE = "ROMANCE", "Romance"


class Room(models.Model):
    code = models.CharField(max_length=6, unique=True)
    host = models.ForeignKey(
        "Player",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hosted_rooms",
    )
    status = models.CharField(max_length=20, choices=RoomStatus.choices, default=RoomStatus.LOBBY)
    current_round = models.PositiveIntegerField(default=0)
    max_rounds = models.PositiveIntegerField(default=5)
    active_question = models.ForeignKey(
        "Question",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="active_in_rooms",
    )
    revealed_answer = models.ForeignKey(
        "Answer",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="revealed_in_rooms",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Room {self.code}"


class Player(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="players")
    name = models.CharField(max_length=32)
    session_id = models.UUIDField(default=uuid.uuid4, editable=False)
    score = models.IntegerField(default=0)
    is_host = models.BooleanField(default=False)
    is_connected = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["room", "name"], name="uq_player_name_in_room"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.room.code})"


class Question(models.Model):
    text = models.TextField()
    type = models.CharField(max_length=16, choices=QuestionType.choices, default=QuestionType.ROMANCE)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.text[:50]


class Round(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="rounds")
    question = models.ForeignKey(Question, on_delete=models.PROTECT, related_name="rounds")
    number = models.PositiveIntegerField()
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    reveal_answer = models.ForeignKey(
        "Answer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="revealed_rounds",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["room", "number"], name="uq_round_room_number"),
        ]

    def __str__(self) -> str:
        return f"{self.room.code}-R{self.number}"


class Answer(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="answers")
    round = models.ForeignKey(Round, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.PROTECT, related_name="answers")
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="answers")
    text = models.TextField()
    normalized_text = models.TextField(blank=True)
    embedding_vector = models.JSONField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["round", "player"],
                name="uq_single_answer_per_round_player",
            )
        ]

    def __str__(self) -> str:
        return f"Answer {self.player.name} {self.round}"


class Guess(models.Model):
    round = models.ForeignKey(Round, on_delete=models.CASCADE, related_name="guesses")
    answer = models.ForeignKey(Answer, on_delete=models.CASCADE, related_name="guesses")
    guesser = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="guesses_made")
    guessed_player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="guesses_received")
    is_correct = models.BooleanField(default=False)
    points_awarded = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["round", "answer", "guesser"],
                name="uq_single_guess_per_answer_player",
            )
        ]

    def __str__(self) -> str:
        return f"{self.guesser.name} -> {self.guessed_player.name} ({self.is_correct})"


class SyncResult(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="sync_results")
    player_one = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="sync_as_first")
    player_two = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="sync_as_second")
    answer_similarity = models.FloatField(default=0.0)
    correct_guess_rate = models.FloatField(default=0.0)
    mutual_selection_rate = models.FloatField(default=0.0)
    sync_percentage = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["room", "player_one", "player_two"],
                name="uq_sync_pair",
            )
        ]

    def __str__(self) -> str:
        return f"{self.player_one.name} <-> {self.player_two.name}: {self.sync_percentage:.2f}"
