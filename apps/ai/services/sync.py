from __future__ import annotations

from dataclasses import dataclass

from apps.game.scoring import SyncComponents, calculate_sync_percentage


@dataclass
class SyncInput:
    answer_similarity: float
    correct_guess_rate: float
    mutual_selection_rate: float


def compute_sync(input_data: SyncInput) -> dict[str, float]:
    components = SyncComponents(
        answer_similarity=input_data.answer_similarity,
        correct_guess_rate=input_data.correct_guess_rate,
        mutual_selection_rate=input_data.mutual_selection_rate,
    )
    percentage = calculate_sync_percentage(components)
    return {
        "answer_similarity": round(input_data.answer_similarity, 4),
        "correct_guess_rate": round(input_data.correct_guess_rate, 4),
        "mutual_selection_rate": round(input_data.mutual_selection_rate, 4),
        "sync_percentage": percentage,
    }
