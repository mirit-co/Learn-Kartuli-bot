# Kartuli SRS Bot

Telegram bot for learning Georgian vocabulary with a strict Spaced Repetition System (SRS).
Source of truth for the learning mechanics is [`task.md`](./task.md); this README is a short
operator-level summary aligned with the current code.

## Current Features

- `/start` onboarding and user creation
- `/learn` strict due-only session (no manual session size)
- `/add` add your own lexical unit as `ka — ru` or `ru — ka`
- `/today` dashboard with day stats
- `/stats` SRS progress (today + box distribution + Box 5 stable)
- `/settings` and `/settings HH:MM Area/City` for reminders
- `/reminder_on` and `/reminder_off`
- `/skill` and `/skill <skill_name> <version>` for skill versions
- SRS boxes with intervals: 1, 2, 7, 14, 30 days
- Binary typed-answer evaluation (`correct` / `wrong`) with deterministic normalization and 1-char Levenshtein tolerance for targets ≥ 4 chars
- In-session buttons: `Показать пример` (only before the answer) and `Не знаю` (= `wrong`)
- User-added pair is split into two cards (`KA→RU` tomorrow, `RU→KA` day after tomorrow)
- Duplicate protection for user-added cards
- SQLite persistence
- A1 seed deck with alphabet + practical topics

## How the SRS Works

Strictly the rules from `task.md` §2–§5. No "almost correct", no same-session relearn,
no per-day new-card limits, no hint ladder.

- **Boxes & intervals**: `1d → 2d → 7d → 14d → 30d`. Box 5 stays at 30 days.
- **Outcomes are binary**: `correct` promotes one box (5 stays 5); `wrong` (or `Не знаю`)
  drops the card straight to Box 1 with `next_review_date = today + 1`, regardless of
  the previous box.
- **Daily session = due queue only**: every card with `next_review_date <= today`,
  ordered by `next_review_date ASC, current_box ASC, created_at ASC`. A card is shown
  at most once per session; if you miss it, it appears tomorrow.
- **Skipped days don't burn cards** — due cards just accumulate.
- **One lexical unit → two independent cards**: `KA→RU` (recognition) and `RU→KA`
  (production). Each has its own box and review date. Currently full pairing applies
  to `/add` cards; the curated A1 seed is `KA→RU` only (RU→KA seed pairing is in roadmap).
- **Hints don't change grading**: `transliteration`, `example_ka`, `example_ru` are
  available *before* the answer via the `Показать пример` button and never affect the
  promotion/demotion logic.

## Storage Layout (mechanics-relevant tables)

- `cards` — shared content of a card: `front_side`, `back_side`, `transliteration`,
  `example_ka/ru`, `accepted_answers_json`, `direction`, `topic`, `source`,
  `owner_user_id` (only for `source='user'`), `lexical_unit_id`, `created_at`.
- `user_cards` — per-user SRS state: `current_box`, `next_review_date`,
  `last_reviewed_at`. The same curated card has a separate state per user.
- `review_events` — per-review log: `was_correct`, `previous_box`, `new_box`,
  `reviewed_at`. Source for the §10 metrics in `task.md`.

## Quick Start

1. Create Telegram bot token via BotFather.
2. Copy `.env.example` to `.env` and fill values.
3. Install dependencies:
   - `python3 -m pip install -e .`
4. Run:
   - `make run`
5. Validate deck data (optional):
   - `make validate-deck`
6. Run tests:
   - `make test`

## Commands

- `/learn` - start due-card review
- `/add` - add card pair in the format `ka — ru` or `ru — ka`
- `/today` - quick daily status
- `/stats` - Прогресс обучения
- `/settings` - show reminder settings
- `/settings HH:MM Area/City` - update reminder time + timezone
- `/reminder_on` - enable reminders
- `/reminder_off` - disable reminders
- `/skill` - list user skill versions
- `/skill <skill_name> <version>` - upgrade one skill version

## Project Layout

- `src/kartuli_bot` - bot app and logic
- `migrations` - SQL schema
- `data/decks` - deck seed files
