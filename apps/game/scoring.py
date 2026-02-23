from __future__ import annotations

from dataclasses import dataclass


CORRECT_GUESS_POINTS = 10
AUTHOR_CAUGHT_POINTS = 2


@dataclass
class SyncComponents:
    answer_similarity: float
    correct_guess_rate: float
    mutual_selection_rate: float


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def score_guess(is_correct: bool) -> int:
    return CORRECT_GUESS_POINTS if is_correct else 0


def score_author_caught(is_correct: bool) -> int:
    return AUTHOR_CAUGHT_POINTS if is_correct else 0


def calculate_sync_percentage(components: SyncComponents) -> float:
    similarity = clamp01(components.answer_similarity)
    guess_rate = clamp01(components.correct_guess_rate)
    mutual = clamp01(components.mutual_selection_rate)
    score = (similarity * 0.4) + (guess_rate * 0.3) + (mutual * 0.3)
    return round(score * 100, 2)
