from __future__ import annotations

import random
import string
from itertools import combinations

from django.db import IntegrityError, transaction
from django.db.models import Q, Sum

from apps.ai.services.embedding import cosine_similarity, encode_text
from apps.ai.services.text import normalize_text

from .models import Answer, Guess, Player, Question, Room, RoomStatus, Round, SyncResult
from .scoring import SyncComponents, calculate_sync_percentage, score_author_caught, score_guess


class GameServiceError(Exception):
    pass


DEFAULT_QUESTIONS = [
    ("What is one tiny thing that instantly makes your day better?", "LIFE"),
    ("What is your most dramatic overreaction this month?", "FUNNY"),
    ("Describe your ideal late-night vibe in one sentence.", "ROMANCE"),
    ("What is one secret talent your friends still underestimate?", "LIFE"),
    ("What is your chaotic comfort food combo?", "FUNNY"),
]


def seed_default_questions() -> None:
    if Question.objects.exists():
        return
    Question.objects.bulk_create(
        [Question(text=text, type=qtype) for text, qtype in DEFAULT_QUESTIONS]
    )


def generate_room_code(length: int = 6) -> str:
    alphabet = string.ascii_uppercase + string.digits
    for _ in range(40):
        code = "".join(random.choices(alphabet, k=length))
        if not Room.objects.filter(code=code).exists():
            return code
    raise GameServiceError("Unable to generate unique room code.")


@transaction.atomic
def create_room_with_host(name: str) -> tuple[Room, Player]:
    code = generate_room_code()
    room = Room.objects.create(code=code, status=RoomStatus.LOBBY)
    host = Player.objects.create(room=room, name=name.strip(), is_host=True)
    room.host = host
    room.save(update_fields=["host", "updated_at"])
    seed_default_questions()
    return room, host


@transaction.atomic
def join_room(code: str, name: str) -> tuple[Room, Player]:
    normalized_code = code.strip().upper()
    try:
        room = Room.objects.get(code=normalized_code)
    except Room.DoesNotExist as exc:
        raise GameServiceError("Room not found.") from exc

    if room.status == RoomStatus.FINISHED:
        raise GameServiceError("This room has already finished.")

    if room.players.count() >= 12:
        raise GameServiceError("Room is full.")

    try:
        player = Player.objects.create(room=room, name=name.strip())
    except IntegrityError as exc:
        raise GameServiceError("Name already taken in this room.") from exc
    return room, player


def _resolve_round(room: Room) -> Round:
    try:
        return Round.objects.get(room=room, number=room.current_round)
    except Round.DoesNotExist as exc:
        raise GameServiceError("No active round found.") from exc


@transaction.atomic
def start_round(room_code: str, question_id: int | None = None) -> tuple[Room, Round]:
    try:
        room = Room.objects.select_for_update().get(code=room_code)
    except Room.DoesNotExist as exc:
        raise GameServiceError("Room not found.") from exc

    if room.current_round >= room.max_rounds:
        raise GameServiceError("Maximum rounds reached.")

    if question_id:
        try:
            question = Question.objects.get(id=question_id, is_active=True)
        except Question.DoesNotExist as exc:
            raise GameServiceError("Invalid question.") from exc
    else:
        question = Question.objects.filter(is_active=True).order_by("?").first()
        if not question:
            raise GameServiceError("No active questions available.")

    next_round_number = room.current_round + 1
    game_round = Round.objects.create(
        room=room,
        question=question,
        number=next_round_number,
    )
    room.current_round = next_round_number
    room.active_question = question
    room.status = RoomStatus.QUESTION
    room.revealed_answer = None
    room.save(
        update_fields=[
            "current_round",
            "active_question",
            "status",
            "revealed_answer",
            "updated_at",
        ]
    )
    return room, game_round


@transaction.atomic
def submit_answer(room_code: str, player_id: str, text: str) -> tuple[Room, Round, Answer]:
    try:
        room = Room.objects.select_for_update().get(code=room_code)
    except Room.DoesNotExist as exc:
        raise GameServiceError("Room not found.") from exc

    if room.status != RoomStatus.QUESTION:
        raise GameServiceError("Room is not accepting answers.")

    game_round = _resolve_round(room)
    try:
        player = Player.objects.get(id=player_id, room=room)
    except Player.DoesNotExist as exc:
        raise GameServiceError("Player not found in room.") from exc

    normalized = normalize_text(text)
    embedding = encode_text(normalized)

    answer, _ = Answer.objects.update_or_create(
        round=game_round,
        player=player,
        defaults={
            "room": room,
            "question": game_round.question,
            "text": text.strip(),
            "normalized_text": normalized,
            "embedding_vector": embedding,
        },
    )
    return room, game_round, answer


@transaction.atomic
def reveal_random_answer(room_code: str) -> tuple[Room, Round, Answer]:
    try:
        room = Room.objects.select_for_update().get(code=room_code)
    except Room.DoesNotExist as exc:
        raise GameServiceError("Room not found.") from exc

    if room.status not in {RoomStatus.QUESTION, RoomStatus.REVEAL}:
        raise GameServiceError("Room cannot reveal answers right now.")

    game_round = _resolve_round(room)
    answers = list(Answer.objects.filter(round=game_round))
    if not answers:
        raise GameServiceError("No answers submitted for this round.")

    revealed = random.choice(answers)
    game_round.reveal_answer = revealed
    game_round.save(update_fields=["reveal_answer"])

    room.revealed_answer = revealed
    room.status = RoomStatus.REVEAL
    room.save(update_fields=["revealed_answer", "status", "updated_at"])

    return room, game_round, revealed


@transaction.atomic
def submit_guess(
    room_code: str,
    player_id: str,
    answer_id: int,
    guessed_player_id: str,
) -> tuple[Room, Round, Guess, bool]:
    try:
        room = Room.objects.select_for_update().get(code=room_code)
    except Room.DoesNotExist as exc:
        raise GameServiceError("Room not found.") from exc

    if room.status != RoomStatus.REVEAL:
        raise GameServiceError("Room is not in reveal phase.")

    game_round = _resolve_round(room)
    try:
        guesser = Player.objects.get(id=player_id, room=room)
        answer = Answer.objects.get(id=answer_id, round=game_round)
        guessed_player = Player.objects.get(id=guessed_player_id, room=room)
    except (Player.DoesNotExist, Answer.DoesNotExist) as exc:
        raise GameServiceError("Guess payload is invalid.") from exc

    if guesser.id == answer.player_id:
        raise GameServiceError("Answer author cannot guess own answer.")

    is_correct = answer.player_id == guessed_player.id
    points = score_guess(is_correct)

    guess, _ = Guess.objects.update_or_create(
        round=game_round,
        answer=answer,
        guesser=guesser,
        defaults={
            "guessed_player": guessed_player,
            "is_correct": is_correct,
            "points_awarded": points,
        },
    )

    recalculate_room_scores(room)

    expected_guesses = room.players.exclude(id=answer.player_id).count()
    submitted_guesses = Guess.objects.filter(round=game_round, answer=answer).count()
    reveal_complete = submitted_guesses >= expected_guesses

    if reveal_complete:
        room.status = RoomStatus.SCOREBOARD
        room.save(update_fields=["status", "updated_at"])

    return room, game_round, guess, reveal_complete


def recalculate_room_scores(room: Room) -> None:
    bonus_for_caught = score_author_caught(True)
    players = list(room.players.all())
    for player in players:
        guess_points = (
            Guess.objects.filter(guesser=player).aggregate(total=Sum("points_awarded"))["total"] or 0
        )
        times_caught = Guess.objects.filter(
            answer__round__room=room,
            answer__player=player,
            is_correct=True,
        ).count()
        player.score = guess_points + (times_caught * bonus_for_caught)
        player.save(update_fields=["score"])


def player_correct_guess_rate(player: Player) -> float:
    total = Guess.objects.filter(guesser=player).count()
    if total == 0:
        return 0.0
    correct = Guess.objects.filter(guesser=player, is_correct=True).count()
    return correct / total


def _pair_answer_similarity(room: Room, p1: Player, p2: Player) -> float:
    round_ids = (
        Round.objects.filter(room=room).values_list("id", flat=True)
    )
    similarities: list[float] = []
    for round_id in round_ids:
        a1 = Answer.objects.filter(round_id=round_id, player=p1).first()
        a2 = Answer.objects.filter(round_id=round_id, player=p2).first()
        if not a1 or not a2 or not a1.embedding_vector or not a2.embedding_vector:
            continue
        similarities.append(cosine_similarity(a1.embedding_vector, a2.embedding_vector))
    if not similarities:
        return 0.0
    return float(sum(similarities) / len(similarities))


def _pair_mutual_selection_rate(room: Room, p1: Player, p2: Player) -> float:
    pair_guesses = Guess.objects.filter(
        Q(guesser=p1, guessed_player=p2) | Q(guesser=p2, guessed_player=p1),
        round__room=room,
    )
    opportunities = Guess.objects.filter(
        Q(guesser=p1) | Q(guesser=p2),
        round__room=room,
    ).count()
    if opportunities == 0:
        return 0.0
    return pair_guesses.count() / opportunities


@transaction.atomic
def calculate_sync_results(room_code: str) -> list[SyncResult]:
    try:
        room = Room.objects.select_for_update().get(code=room_code)
    except Room.DoesNotExist as exc:
        raise GameServiceError("Room not found.") from exc

    players = list(room.players.order_by("joined_at"))
    if len(players) < 2:
        raise GameServiceError("Need at least two players to compute sync.")

    SyncResult.objects.filter(room=room).delete()
    created: list[SyncResult] = []
    for p1, p2 in combinations(players, 2):
        answer_similarity = _pair_answer_similarity(room, p1, p2)
        correct_guess_rate = (player_correct_guess_rate(p1) + player_correct_guess_rate(p2)) / 2
        mutual_selection_rate = _pair_mutual_selection_rate(room, p1, p2)

        components = SyncComponents(
            answer_similarity=answer_similarity,
            correct_guess_rate=correct_guess_rate,
            mutual_selection_rate=mutual_selection_rate,
        )

        created.append(
            SyncResult.objects.create(
                room=room,
                player_one=p1,
                player_two=p2,
                answer_similarity=answer_similarity,
                correct_guess_rate=correct_guess_rate,
                mutual_selection_rate=mutual_selection_rate,
                sync_percentage=calculate_sync_percentage(components),
            )
        )

    room.status = RoomStatus.FINISHED
    room.save(update_fields=["status", "updated_at"])
    return created


def get_leaderboard(room: Room) -> list[dict]:
    players = room.players.order_by("-score", "joined_at")
    return [
        {
            "id": str(player.id),
            "name": player.name,
            "score": player.score,
            "is_host": player.is_host,
        }
        for player in players
    ]


def get_room_snapshot(room: Room) -> dict:
    current_round = (
        Round.objects.filter(room=room, number=room.current_round)
        .select_related("question")
        .first()
    )
    revealed_answer = room.revealed_answer
    return {
        "room_code": room.code,
        "status": room.status,
        "round": room.current_round,
        "max_rounds": room.max_rounds,
        "question": current_round.question.text if current_round else None,
        "question_type": current_round.question.type if current_round else None,
        "revealed_answer_id": revealed_answer.id if revealed_answer else None,
        "revealed_answer_text": revealed_answer.text if revealed_answer else None,
        "players": get_leaderboard(room),
    }
