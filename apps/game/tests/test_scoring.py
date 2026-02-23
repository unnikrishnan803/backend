from django.test import SimpleTestCase

from apps.game.scoring import SyncComponents, calculate_sync_percentage, score_guess


class ScoringTests(SimpleTestCase):
    def test_correct_guess_points(self):
        self.assertEqual(score_guess(True), 10)
        self.assertEqual(score_guess(False), 0)

    def test_sync_weight_formula(self):
        components = SyncComponents(
            answer_similarity=0.8,
            correct_guess_rate=0.5,
            mutual_selection_rate=0.25,
        )
        self.assertEqual(calculate_sync_percentage(components), 54.5)
