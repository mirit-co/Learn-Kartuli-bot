from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from kartuli_bot.db import Database


class DatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(__file__).resolve().parents[1]
        self.db_path = str(Path(self.tmp.name) / "test.db")
        self.db = Database(
            db_path=self.db_path,
            migrations_dir=str(root / "migrations"),
            deck_path=str(root / "data" / "decks" / "a1_seed.json"),
        )
        self.db.initialize()
        self.user_id = self.db.ensure_user(telegram_id=123456, default_timezone="Europe/Tbilisi")
        self.db.ensure_user_cards(self.user_id)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_new_cards_available_for_new_user(self) -> None:
        self.assertEqual(self.db.get_due_count(self.user_id), 0)
        self.assertGreater(self.db.get_new_card_count(self.user_id), 0)
        card_ids = self.db.get_session_card_ids_limited(self.user_id, 10)
        self.assertEqual(len(card_ids), 10)

    def test_review_updates_box_and_logs_event(self) -> None:
        card_ids = self.db.get_session_card_ids_limited(self.user_id, 1)
        self.assertEqual(len(card_ids), 1)
        card_id = card_ids[0]
        self.db.review_card(self.user_id, card_id, was_correct=True)

        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT current_box FROM user_cards WHERE user_id = ? AND card_id = ?",
                (self.user_id, card_id),
            ).fetchone()
            self.assertEqual(int(row["current_box"]), 2)

            event = conn.execute(
                "SELECT was_correct, previous_box, new_box FROM review_events WHERE user_id = ? ORDER BY id DESC",
                (self.user_id,),
            ).fetchone()
            self.assertEqual(int(event["was_correct"]), 1)
            self.assertEqual(int(event["previous_box"]), 1)
            self.assertEqual(int(event["new_box"]), 2)

    def test_reminder_due_query_and_dedup(self) -> None:
        self.db.update_reminder_settings(self.user_id, reminder_time="09:00", timezone="UTC", enabled=True)
        due = self.db.get_users_due_for_reminder(datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc))
        self.assertEqual(len(due), 1)
        self.db.mark_reminder_sent(self.user_id, due[0]["local_date"])
        due_again = self.db.get_users_due_for_reminder(datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc))
        self.assertEqual(len(due_again), 0)


if __name__ == "__main__":
    unittest.main()
