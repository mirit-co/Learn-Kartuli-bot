from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
import sqlite3
from zoneinfo import ZoneInfo

from .deck_quality import load_deck, validate_deck
from .srs import next_box_after_review, next_review_date_for_box


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class Database:
    @staticmethod
    def _default_skill_names() -> tuple[str, ...]:
        from .skills.registry import SKILLS

        return tuple(SKILLS.keys())

    def __init__(self, db_path: str, migrations_dir: str, deck_path: str) -> None:
        self.db_path = db_path
        self.migrations_dir = migrations_dir
        self.deck_path = deck_path

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def initialize(self) -> None:
        with self.connect() as conn:
            self._run_migrations(conn)
            self._sync_seed_cards(conn)

    def _run_migrations(self, conn: sqlite3.Connection) -> None:
        migrations_path = Path(self.migrations_dir)
        for migration_file in sorted(migrations_path.glob("*.sql")):
            migration_sql = migration_file.read_text(encoding="utf-8")
            try:
                conn.executescript(migration_sql)
            except sqlite3.OperationalError as exc:
                message = str(exc).lower()
                if "duplicate column name" in message:
                    continue
                raise

    def _sync_seed_cards(self, conn: sqlite3.Connection) -> None:
        """Insert any seed cards from the deck JSON that aren't already in the DB.

        Dedup key: (front_side, back_side, topic) within the curated/base deck
        (owner_user_id IS NULL). User-added cards are not affected.
        Safe to call on every startup so the welcome card count tracks the seed.
        """
        data = load_deck(self.deck_path)
        errors = validate_deck(data)
        if errors:
            raise ValueError("Deck validation failed: " + "; ".join(errors[:5]))
        existing = {
            (row["front_side"], row["back_side"], row["topic"])
            for row in conn.execute(
                "SELECT front_side, back_side, topic FROM cards WHERE owner_user_id IS NULL"
            ).fetchall()
        }
        new_entries = [
            entry
            for entry in data
            if (entry["front_side"], entry["back_side"], entry["topic"]) not in existing
        ]
        if not new_entries:
            return
        conn.executemany(
            """
            INSERT INTO cards(front_side, back_side, topic, transliteration)
            VALUES(:front_side, :back_side, :topic, :transliteration)
            """,
            new_entries,
        )
        conn.execute(
            """
            UPDATE cards
            SET lexical_unit_id = id
            WHERE lexical_unit_id IS NULL
            """
        )
        conn.commit()

    def ensure_user(self, telegram_id: int, default_timezone: str) -> int:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT id FROM users WHERE telegram_id = ?",
                (telegram_id,),
            ).fetchone()
            if row:
                user_id = int(row["id"])
                for skill_name in self._default_skill_names():
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO skill_configs(user_id, skill_name, skill_version, config_json)
                        VALUES(?, ?, '1.0.0', '{}')
                        """,
                        (user_id, skill_name),
                    )
                conn.commit()
                return user_id
            cursor = conn.execute(
                """
                INSERT INTO users(telegram_id, timezone)
                VALUES(?, ?)
                """,
                (telegram_id, default_timezone),
            )
            user_id = int(cursor.lastrowid)
            conn.execute(
                """
                INSERT INTO reminder_settings(user_id, reminder_time, enabled, timezone)
                VALUES(?, '10:00', 1, ?)
                """,
                (user_id, default_timezone),
            )
            for skill_name in self._default_skill_names():
                conn.execute(
                    """
                    INSERT INTO skill_configs(user_id, skill_name, skill_version, config_json)
                    VALUES(?, ?, '1.0.0', '{}')
                    """,
                    (user_id, skill_name),
                )
            conn.commit()
            return user_id

    def ensure_user_cards(self, user_id: int) -> None:
        tomorrow = next_review_date_for_box(1).isoformat()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO user_cards(user_id, card_id, current_box, next_review_date)
                SELECT ?, c.id, 1, ?
                FROM cards c
                WHERE c.owner_user_id IS NULL OR c.owner_user_id = ?
                """,
                (user_id, tomorrow, user_id),
            )
            conn.commit()

    def count_base_deck_cards(self) -> int:
        """Count cards in the shared A1 deck (excludes user-added cards)."""
        with self.connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM cards WHERE owner_user_id IS NULL"
            ).fetchone()
            return int(row["c"])

    def get_due_card(self, user_id: int) -> sqlite3.Row | None:
        today = date.today().isoformat()
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT c.id, c.front_side, c.back_side, c.transliteration, uc.current_box
                FROM user_cards uc
                JOIN cards c ON c.id = uc.card_id
                WHERE uc.user_id = ? AND uc.next_review_date <= ?
                ORDER BY
                    uc.next_review_date ASC,
                    CASE WHEN uc.last_reviewed_at IS NULL THEN 1 ELSE 0 END ASC,
                    uc.current_box ASC,
                    c.created_at ASC
                LIMIT 1
                """,
                (user_id, today),
            ).fetchone()

    def get_due_counts_per_box(self, user_id: int) -> dict[int, int]:
        today = date.today().isoformat()
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT current_box, COUNT(*) AS cnt
                FROM user_cards
                WHERE user_id = ? AND next_review_date <= ?
                GROUP BY current_box
                ORDER BY current_box
                """,
                (user_id, today),
            ).fetchall()
            return {int(r["current_box"]): int(r["cnt"]) for r in rows}

    def get_session_card_ids_limited(self, user_id: int, limit: int) -> list[int]:
        """Build a due-only session queue (strict SRS).

        Sort order:
          1. next_review_date ASC   — oldest overdue first
          2. last_reviewed_at IS NULL ASC — reviewed-at-least-once before brand-new
          3. current_box ASC        — lower boxes first within same date
          4. created_at ASC         — stable tie-break
        """
        today = date.today().isoformat()
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT uc.card_id
                FROM user_cards uc
                JOIN cards c ON c.id = uc.card_id
                WHERE uc.user_id = ? AND uc.next_review_date <= ?
                ORDER BY
                    uc.next_review_date ASC,
                    CASE WHEN uc.last_reviewed_at IS NULL THEN 1 ELSE 0 END ASC,
                    uc.current_box ASC,
                    c.created_at ASC
                LIMIT ?
                """,
                (user_id, today, limit),
            ).fetchall()
            return [int(r["card_id"]) for r in rows]

    def get_due_card_ids(self, user_id: int) -> list[int]:
        today = date.today().isoformat()
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT uc.card_id
                FROM user_cards uc
                JOIN cards c ON c.id = uc.card_id
                WHERE uc.user_id = ? AND uc.next_review_date <= ?
                ORDER BY
                    uc.next_review_date ASC,
                    CASE WHEN uc.last_reviewed_at IS NULL THEN 1 ELSE 0 END ASC,
                    uc.current_box ASC,
                    c.created_at ASC
                """,
                (user_id, today),
            ).fetchall()
            return [int(r["card_id"]) for r in rows]

    def get_new_card_count(self, user_id: int) -> int:
        return 0

    def get_card_for_review(self, user_id: int, card_id: int) -> sqlite3.Row | None:
        """Fetch card data without checking next_review_date (for pre-selected sessions)."""
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT
                    c.id,
                    c.front_side,
                    c.back_side,
                    c.transliteration,
                    c.example_ka,
                    c.example_ru,
                    c.accepted_answers_json,
                    c.direction,
                    uc.current_box
                FROM user_cards uc
                JOIN cards c ON c.id = uc.card_id
                WHERE uc.user_id = ? AND uc.card_id = ?
                LIMIT 1
                """,
                (user_id, card_id),
            ).fetchone()

    def get_due_card_by_id(self, user_id: int, card_id: int) -> sqlite3.Row | None:
        today = date.today().isoformat()
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT
                    c.id,
                    c.front_side,
                    c.back_side,
                    c.transliteration,
                    c.example_ka,
                    c.example_ru,
                    c.accepted_answers_json,
                    c.direction,
                    uc.current_box
                FROM user_cards uc
                JOIN cards c ON c.id = uc.card_id
                WHERE uc.user_id = ? AND uc.card_id = ? AND uc.next_review_date <= ?
                LIMIT 1
                """,
                (user_id, card_id, today),
            ).fetchone()

    def get_due_count(self, user_id: int) -> int:
        today = date.today().isoformat()
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM user_cards
                WHERE user_id = ? AND next_review_date <= ?
                """,
                (user_id, today),
            ).fetchone()
            return int(row["c"])

    def get_due_tomorrow_count(self, user_id: int) -> int:
        today = date.today().isoformat()
        tomorrow = next_review_date_for_box(1).isoformat()
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(DISTINCT re.card_id) AS c
                FROM review_events re
                JOIN user_cards uc
                  ON uc.user_id = re.user_id
                 AND uc.card_id = re.card_id
                WHERE re.user_id = ?
                  AND DATE(re.reviewed_at) = ?
                  AND uc.next_review_date = ?
                """,
                (user_id, today, tomorrow),
            ).fetchone()
            return int(row["c"])

    def get_box_distribution(self, user_id: int) -> dict[int, int]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT current_box, COUNT(*) AS cnt
                FROM user_cards
                WHERE user_id = ?
                GROUP BY current_box
                ORDER BY current_box ASC
                """,
                (user_id,),
            ).fetchall()
            return {int(r["current_box"]): int(r["cnt"]) for r in rows}

    def get_box5_stable_30d_count(self, user_id: int) -> int:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM user_cards
                WHERE user_id = ?
                  AND current_box = 5
                  AND last_reviewed_at IS NOT NULL
                  AND DATE(last_reviewed_at) <= DATE('now', '-30 day')
                """,
                (user_id,),
            ).fetchone()
            return int(row["c"])

    def get_avg_days_box1_to_box5_by_topic(self, user_id: int) -> dict[str, float]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                WITH first_seen AS (
                    SELECT card_id, MIN(DATE(reviewed_at)) AS first_day
                    FROM review_events
                    WHERE user_id = ?
                    GROUP BY card_id
                ),
                first_box5 AS (
                    SELECT card_id, MIN(DATE(reviewed_at)) AS box5_day
                    FROM review_events
                    WHERE user_id = ? AND new_box = 5
                    GROUP BY card_id
                )
                SELECT c.topic AS topic,
                       AVG(julianday(fb.box5_day) - julianday(fs.first_day)) AS avg_days
                FROM first_seen fs
                JOIN first_box5 fb ON fb.card_id = fs.card_id
                JOIN cards c ON c.id = fs.card_id
                GROUP BY c.topic
                ORDER BY c.topic ASC
                """,
                (user_id, user_id),
            ).fetchall()
            return {
                str(r["topic"]): round(float(r["avg_days"]), 1)
                for r in rows
                if r["avg_days"] is not None
            }

    def add_user_lexical_unit(
        self,
        user_id: int,
        ka_text: str,
        ru_text: str,
        transliteration: str | None = None,
        example_ka: str | None = None,
        example_ru: str | None = None,
        topic: str = "other",
    ) -> tuple[int, int]:
        now = _utc_now_iso()
        tomorrow = next_review_date_for_box(1).isoformat()
        day_after_tomorrow = next_review_date_for_box(1, next_review_date_for_box(1)).isoformat()
        accepted_ru_json = json.dumps([ru_text], ensure_ascii=False)
        accepted_ka_json = json.dumps([ka_text], ensure_ascii=False)
        with self.connect() as conn:
            # Detect duplicates among cards available to this user.
            dup = conn.execute(
                """
                SELECT c.lexical_unit_id
                FROM cards c
                JOIN user_cards uc ON uc.card_id = c.id
                WHERE uc.user_id = ?
                  AND (
                    (c.direction = 'ka_ru' AND lower(trim(c.front_side)) = lower(trim(?)) AND lower(trim(c.back_side)) = lower(trim(?)))
                    OR
                    (c.direction = 'ru_ka' AND lower(trim(c.front_side)) = lower(trim(?)) AND lower(trim(c.back_side)) = lower(trim(?)))
                  )
                LIMIT 1
                """,
                (user_id, ka_text, ru_text, ru_text, ka_text),
            ).fetchone()
            if dup:
                raise ValueError("duplicate_lexical_unit")

            ka_cursor = conn.execute(
                """
                INSERT INTO cards(
                    front_side, back_side, topic, transliteration, direction, accepted_answers_json,
                    letter, example_ka, example_ru, source, owner_user_id
                )
                VALUES(?, ?, ?, ?, 'ka_ru', ?, NULL, ?, ?, 'user', ?)
                """,
                (
                    ka_text,
                    ru_text,
                    topic,
                    transliteration,
                    accepted_ru_json,
                    example_ka,
                    example_ru,
                    user_id,
                ),
            )
            ka_card_id = int(ka_cursor.lastrowid)
            conn.execute(
                "UPDATE cards SET lexical_unit_id = ? WHERE id = ?",
                (ka_card_id, ka_card_id),
            )

            ru_cursor = conn.execute(
                """
                INSERT INTO cards(
                    lexical_unit_id, front_side, back_side, topic, transliteration, direction,
                    accepted_answers_json, letter, example_ka, example_ru, source, owner_user_id
                )
                VALUES(?, ?, ?, ?, ?, 'ru_ka', ?, NULL, ?, ?, 'user', ?)
                """,
                (
                    ka_card_id,
                    ru_text,
                    ka_text,
                    topic,
                    None,
                    accepted_ka_json,
                    example_ka,
                    example_ru,
                    user_id,
                ),
            )
            ru_card_id = int(ru_cursor.lastrowid)

            conn.execute(
                """
                INSERT OR IGNORE INTO user_cards(user_id, card_id, current_box, next_review_date, last_reviewed_at)
                VALUES(?, ?, 1, ?, ?)
                """,
                (user_id, ka_card_id, tomorrow, now),
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO user_cards(user_id, card_id, current_box, next_review_date, last_reviewed_at)
                VALUES(?, ?, 1, ?, ?)
                """,
                (user_id, ru_card_id, day_after_tomorrow, now),
            )
            conn.commit()
            return ka_card_id, ru_card_id

    def get_today_review_stats(self, user_id: int) -> dict[str, int]:
        today = date.today().isoformat()
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS reviewed,
                    COALESCE(SUM(was_correct), 0) AS remembered
                FROM review_events
                WHERE user_id = ? AND DATE(reviewed_at) = ?
                """,
                (user_id, today),
            ).fetchone()
            reviewed = int(row["reviewed"])
            remembered = int(row["remembered"])
            forgot = reviewed - remembered
            return {"reviewed": reviewed, "remembered": remembered, "forgot": forgot}

    def get_reminder_settings(self, user_id: int) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT reminder_time, enabled, timezone
                FROM reminder_settings
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()

    def update_reminder_settings(
        self,
        user_id: int,
        reminder_time: str | None = None,
        timezone: str | None = None,
        enabled: bool | None = None,
    ) -> None:
        with self.connect() as conn:
            current = conn.execute(
                "SELECT reminder_time, timezone, enabled FROM reminder_settings WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if not current:
                return
            conn.execute(
                """
                UPDATE reminder_settings
                SET reminder_time = ?, timezone = ?, enabled = ?
                WHERE user_id = ?
                """,
                (
                    reminder_time if reminder_time is not None else current["reminder_time"],
                    timezone if timezone is not None else current["timezone"],
                    int(enabled) if enabled is not None else int(current["enabled"]),
                    user_id,
                ),
            )
            if timezone is not None:
                conn.execute("UPDATE users SET timezone = ? WHERE id = ?", (timezone, user_id))
            conn.commit()

    def get_users_due_for_reminder(self, now_utc: datetime) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                  u.id AS user_id,
                  u.telegram_id AS telegram_id,
                  rs.timezone AS timezone,
                  rs.reminder_time AS reminder_time,
                  rs.enabled AS enabled
                FROM users u
                JOIN reminder_settings rs ON rs.user_id = u.id
                WHERE rs.enabled = 1
                """
            ).fetchall()
            due: list[dict] = []
            for row in rows:
                timezone = row["timezone"]
                try:
                    local = now_utc.astimezone(ZoneInfo(timezone))
                except (KeyError, ValueError):
                    continue
                hh_mm = local.strftime("%H:%M")
                local_date = local.date().isoformat()
                if hh_mm != row["reminder_time"]:
                    continue
                already_sent = conn.execute(
                    """
                    SELECT 1 FROM reminder_dispatches
                    WHERE user_id = ? AND local_date = ?
                    LIMIT 1
                    """,
                    (row["user_id"], local_date),
                ).fetchone()
                if already_sent:
                    continue
                due.append(
                    {
                        "user_id": int(row["user_id"]),
                        "telegram_id": int(row["telegram_id"]),
                        "local_date": local_date,
                    }
                )
            return due

    def mark_reminder_sent(self, user_id: int, local_date: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO reminder_dispatches(user_id, local_date)
                VALUES(?, ?)
                """,
                (user_id, local_date),
            )
            conn.commit()

    def review_card(self, user_id: int, card_id: int, was_correct: bool) -> None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT current_box FROM user_cards
                WHERE user_id = ? AND card_id = ?
                """,
                (user_id, card_id),
            ).fetchone()
            if not row:
                return
            previous_box = int(row["current_box"])
            new_box = next_box_after_review(previous_box, was_correct)
            next_review = next_review_date_for_box(new_box).isoformat()
            now = _utc_now_iso()
            conn.execute(
                """
                UPDATE user_cards
                SET current_box = ?, next_review_date = ?, last_reviewed_at = ?
                WHERE user_id = ? AND card_id = ?
                """,
                (new_box, next_review, now, user_id, card_id),
            )
            conn.execute(
                """
                INSERT INTO review_events(user_id, card_id, was_correct, previous_box, new_box, reviewed_at)
                VALUES(?, ?, ?, ?, ?, ?)
                """,
                (user_id, card_id, int(was_correct), previous_box, new_box, now),
            )
            conn.commit()

    def get_skill_configs(self, user_id: int) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT skill_name, skill_version, config_json
                FROM skill_configs
                WHERE user_id = ?
                ORDER BY skill_name ASC
                """,
                (user_id,),
            ).fetchall()

    def update_skill_config(self, user_id: int, skill_name: str, skill_version: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE skill_configs
                SET skill_version = ?
                WHERE user_id = ? AND skill_name = ?
                """,
                (skill_version, user_id, skill_name),
            )
            conn.commit()
