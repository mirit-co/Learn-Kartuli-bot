# Kartuli Leitner Bot

Telegram bot for learning Georgian vocabulary with the Leitner spaced-repetition system.

## MVP Features

- `/start` onboarding and user creation
- `/learn` daily due-card session
- `/today` dashboard with day stats
- `/settings` and `/settings HH:MM Area/City` for reminders
- `/skill` and `/skill <skill_name> <version>` for skill versions
- Leitner boxes with intervals: 1, 2, 7, 14, 30 days
- Button-based self-assessment: `I remembered` / `I forgot`
- SQLite persistence
- A1 seed deck with alphabet + practical topics

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

## Project Layout

- `src/kartuli_bot` - bot app and logic
- `migrations` - SQL schema
- `data/decks` - deck seed files
