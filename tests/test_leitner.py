from datetime import date
import unittest

from kartuli_bot.leitner import next_box_after_review, next_review_date_for_box


class LeitnerTests(unittest.TestCase):
    def test_correct_answer_moves_to_next_box(self) -> None:
        self.assertEqual(next_box_after_review(1, True), 2)
        self.assertEqual(next_box_after_review(4, True), 5)
        self.assertEqual(next_box_after_review(5, True), 5)

    def test_wrong_answer_resets_to_box_one(self) -> None:
        self.assertEqual(next_box_after_review(5, False), 1)
        self.assertEqual(next_box_after_review(2, False), 1)

    def test_next_review_date_interval(self) -> None:
        anchor = date(2026, 1, 1)
        self.assertEqual(next_review_date_for_box(1, anchor).isoformat(), "2026-01-02")
        self.assertEqual(next_review_date_for_box(2, anchor).isoformat(), "2026-01-03")
        self.assertEqual(next_review_date_for_box(3, anchor).isoformat(), "2026-01-08")
        self.assertEqual(next_review_date_for_box(4, anchor).isoformat(), "2026-01-15")
        self.assertEqual(next_review_date_for_box(5, anchor).isoformat(), "2026-01-31")


if __name__ == "__main__":
    unittest.main()
