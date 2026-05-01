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
        total = self.db.count_base_deck_cards()
        self.assertGreater(total, 0)
        self.assertEqual(self.db.get_due_count(self.user_id), total)
        card_ids = self.db.get_session_card_ids_limited(self.user_id, 10)
        self.assertEqual(len(card_ids), min(10, total))

    def test_due_queue_orders_by_due_then_box(self) -> None:
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT card_id FROM user_cards WHERE user_id = ? ORDER BY card_id ASC LIMIT 3",
                (self.user_id,),
            ).fetchall()
            card_ids = [int(r["card_id"]) for r in rows]
            # Push all cards to the future so only the 3 test cards are due.
            conn.execute(
                "UPDATE user_cards SET next_review_date = date('now', '+10 day') WHERE user_id = ?",
                (self.user_id,),
            )
            conn.execute(
                "UPDATE user_cards SET next_review_date = date('now'), current_box = 3 WHERE user_id = ? AND card_id = ?",
                (self.user_id, card_ids[0]),
            )
            conn.execute(
                "UPDATE user_cards SET next_review_date = date('now'), current_box = 1 WHERE user_id = ? AND card_id = ?",
                (self.user_id, card_ids[1]),
            )
            conn.execute(
                "UPDATE user_cards SET next_review_date = date('now', '-1 day'), current_box = 5 WHERE user_id = ? AND card_id = ?",
                (self.user_id, card_ids[2]),
            )
            conn.commit()
        due_ids = self.db.get_due_card_ids(self.user_id)
        self.assertEqual(due_ids[:3], [card_ids[2], card_ids[1], card_ids[0]])

    def test_review_updates_box_and_logs_event(self) -> None:
        with self.db.connect() as conn:
            card_id = int(
                conn.execute(
                    "SELECT card_id FROM user_cards WHERE user_id = ? ORDER BY card_id ASC LIMIT 1",
                    (self.user_id,),
                ).fetchone()["card_id"]
            )
            conn.execute(
                "UPDATE user_cards SET next_review_date = date('now') WHERE user_id = ? AND card_id = ?",
                (self.user_id, card_id),
            )
            conn.commit()
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

    def test_due_tomorrow_count_tracks_only_reviewed_today(self) -> None:
        # Seeded cards are initially scheduled for tomorrow, but should not
        # be counted in the "session summary" metric before any review today.
        self.assertEqual(self.db.get_due_tomorrow_count(self.user_id), 0)

        with self.db.connect() as conn:
            card_id = int(
                conn.execute(
                    "SELECT card_id FROM user_cards WHERE user_id = ? ORDER BY card_id ASC LIMIT 1",
                    (self.user_id,),
                ).fetchone()["card_id"]
            )
            conn.execute(
                "UPDATE user_cards SET next_review_date = date('now') WHERE user_id = ? AND card_id = ?",
                (self.user_id, card_id),
            )
            conn.commit()

        self.db.review_card(self.user_id, card_id, was_correct=False)
        self.assertEqual(self.db.get_due_tomorrow_count(self.user_id), 1)

    def test_add_user_lexical_unit_creates_two_cards(self) -> None:
        ka_card_id, ru_card_id = self.db.add_user_lexical_unit(
            user_id=self.user_id,
            ka_text="ტესტსიტყვა",
            ru_text="тестовое",
            topic="market",
        )
        with self.db.connect() as conn:
            ka_row = conn.execute(
                """
                SELECT c.direction, c.source, c.owner_user_id, uc.current_box, uc.next_review_date
                FROM cards c
                JOIN user_cards uc ON uc.card_id = c.id
                WHERE uc.user_id = ? AND c.id = ?
                """,
                (self.user_id, ka_card_id),
            ).fetchone()
            ru_row = conn.execute(
                """
                SELECT c.direction, c.source, c.owner_user_id, uc.current_box, uc.next_review_date
                FROM cards c
                JOIN user_cards uc ON uc.card_id = c.id
                WHERE uc.user_id = ? AND c.id = ?
                """,
                (self.user_id, ru_card_id),
            ).fetchone()
            self.assertEqual(str(ka_row["direction"]), "ka_ru")
            self.assertEqual(str(ru_row["direction"]), "ru_ka")
            self.assertEqual(str(ka_row["source"]), "user")
            self.assertEqual(int(ka_row["owner_user_id"]), self.user_id)
            self.assertEqual(int(ka_row["current_box"]), 1)
            self.assertEqual(int(ru_row["current_box"]), 1)
            self.assertLess(str(ka_row["next_review_date"]), str(ru_row["next_review_date"]))

    def test_seed_sync_is_idempotent_and_picks_up_new_entries(self) -> None:
        baseline = self.db.count_base_deck_cards()
        self.db.initialize()
        self.assertEqual(self.db.count_base_deck_cards(), baseline)

        extra_deck = Path(self.tmp.name) / "extra.json"
        extra_deck.write_text(
            '[{"front_side":"ტესტ-ფრონტ","back_side":"тест-фронт",'
            '"topic":"other","transliteration":"test-front"}]',
            encoding="utf-8",
        )
        self.db.deck_path = str(extra_deck)
        self.db.initialize()
        self.assertEqual(self.db.count_base_deck_cards(), baseline + 1)
        self.db.initialize()
        self.assertEqual(self.db.count_base_deck_cards(), baseline + 1)

    def test_count_base_deck_cards_excludes_user_added(self) -> None:
        baseline = self.db.count_base_deck_cards()
        self.assertGreater(baseline, 0)
        with self.db.connect() as conn:
            seed_total = int(
                conn.execute("SELECT COUNT(*) AS c FROM cards").fetchone()["c"]
            )
        self.assertEqual(baseline, seed_total)

        self.db.add_user_lexical_unit(
            user_id=self.user_id,
            ka_text="ტესტსიტყვა",
            ru_text="тестовое",
            topic="market",
        )
        self.assertEqual(self.db.count_base_deck_cards(), baseline)

    def test_reminder_due_query_and_dedup(self) -> None:
        self.db.update_reminder_settings(self.user_id, reminder_time="09:00", timezone="UTC", enabled=True)
        due = self.db.get_users_due_for_reminder(datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc))
        self.assertEqual(len(due), 1)
        self.db.mark_reminder_sent(self.user_id, due[0]["local_date"])
        due_again = self.db.get_users_due_for_reminder(datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc))
        self.assertEqual(len(due_again), 0)


if __name__ == "__main__":
    unittest.main()
