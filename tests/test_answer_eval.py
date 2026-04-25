import unittest

from kartuli_bot.handlers.learn import _accepted_answers, _is_correct_answer


class AnswerEvaluatorTests(unittest.TestCase):
    def test_exact_and_accepted_answers(self) -> None:
        accepted = _accepted_answers("пакет", '["сумка", "пакетик"]')
        self.assertTrue(_is_correct_answer("ПАКЕТ", accepted))
        self.assertTrue(_is_correct_answer("сумка", accepted))
        self.assertFalse(_is_correct_answer("чемодан", accepted))

    def test_typo_tolerance_for_long_words(self) -> None:
        accepted = _accepted_answers("магазин", "[]")
        self.assertTrue(_is_correct_answer("магазинн", accepted))
        self.assertFalse(_is_correct_answer("магаз", accepted))

    def test_no_tolerance_for_short_words(self) -> None:
        accepted = _accepted_answers("дом", "[]")
        self.assertFalse(_is_correct_answer("дос", accepted))


if __name__ == "__main__":
    unittest.main()
