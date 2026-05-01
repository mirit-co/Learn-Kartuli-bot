# CLAUDE.md — Agent Reference

## Project

Telegram bot for learning Georgian vocabulary using a Spaced Repetition System (SRS).
Language: Python 3.11+. Framework: aiogram 3. Storage: SQLite.

---

## Repository Layout

```
Learn-Kartuli-bot/
├── src/kartuli_bot/        # Main application package
│   ├── main.py             # Entry point: init DB, register handlers, start polling
│   ├── config.py           # Settings loaded from env vars (BOT_TOKEN, DB_PATH, DEFAULT_TIMEZONE)
│   ├── db.py               # Database class: migrations, seed sync, all queries
│   ├── srs.py              # SRS logic: box intervals, next_review_date calculation
│   ├── scheduler.py        # Background task: checks and sends reminders every 60s
│   ├── keyboards.py        # Inline keyboard builders
│   ├── deck_quality.py     # Deck JSON loader and validator
│   ├── handlers/
│   │   ├── start.py        # /start — onboarding, user creation
│   │   ├── learn.py        # /learn — SRS review session
│   │   ├── add.py          # /add — user adds vocabulary pair
│   │   ├── stats.py        # /stats, /today — progress dashboards
│   │   ├── settings.py     # /settings, /reminder_on, /reminder_off
│   │   └── skill.py        # /skill — manage learning skill versions
│   └── skills/
│       ├── registry.py     # SKILLS dict: name → SkillConfig
│       └── service.py      # Skill upgrade logic
├── migrations/             # SQL migration files (applied in filename order on startup)
├── data/decks/
│   └── a1_seed.json        # Curated A1 seed deck (baked into Docker image)
├── skills/                 # Skill definition files (JSON)
├── tests/                  # Unit tests (unittest)
├── scripts/
│   └── validate_deck.py    # Deck JSON validation script
├── Dockerfile
├── docker-compose.yml
├── .github/workflows/
│   └── deploy.yml          # CI/CD: test → SSH deploy on push to main
├── pyproject.toml          # Dependencies and package config
└── Makefile                # run / test / validate-deck
```

---

## Key Files

| File | Role |
|------|------|
| `src/kartuli_bot/main.py` | Entry point. Resolves `root` path as `Path(__file__).parents[2]` (= repo root). Passes `migrations_dir=root/migrations`, `deck_path=root/data/decks/a1_seed.json` to Database. |
| `src/kartuli_bot/db.py` | Single `Database` class. Runs migrations on `__init__`, syncs seed cards. All SQL is here. |
| `src/kartuli_bot/srs.py` | Pure functions: box intervals `[1, 2, 7, 14, 30]`, `next_review_date`, promotion/demotion. |
| `src/kartuli_bot/config.py` | `load_settings()` reads env vars via python-dotenv. `DB_PATH` is resolved to absolute path. |
| `data/decks/a1_seed.json` | Seed vocabulary. Loaded at every startup; new cards are inserted, existing ones are skipped (`INSERT OR IGNORE`). |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BOT_TOKEN` | required | Telegram bot token from BotFather |
| `DB_PATH` | `kartuli.db` | Path to SQLite database file |
| `DEFAULT_TIMEZONE` | `Europe/Tbilisi` | Fallback timezone for reminders |

---

## Running Locally

```bash
# Install dependencies
pip install -e .

# Create .env (copy from example, fill BOT_TOKEN)
cp .env.example .env

# Run bot
make run

# Run tests
make test

# Validate seed deck
make validate-deck
```

With Docker locally:
```bash
# .env is picked up automatically by docker compose
docker compose up --build
```

---

## Database Schema (mechanics-relevant)

- **`cards`** — vocabulary content. `front_side`, `back_side`, `transliteration`, `direction` (ka→ru / ru→ka), `topic`, `source` (`seed` | `user`), `owner_user_id` (user-added only), `lexical_unit_id` (links the two cards of a pair).
- **`user_cards`** — per-user SRS state. `current_box` (1–5), `next_review_date`, `last_reviewed_at`.
- **`review_events`** — history log per review. `was_correct`, `previous_box`, `new_box`, `reviewed_at`.
- **`users`** — Telegram user registration, reminder settings, timezone.
- **`skill_configs`** — per-user skill version selections.

Migrations in `migrations/` are applied once on startup in filename-sorted order.

---

## SRS Rules (source of truth: task.md)

- **Boxes**: 1 → 2 → 3 → 4 → 5. Intervals: 1, 2, 7, 14, 30 days.
- **Correct**: promotes one box (box 5 stays at 5).
- **Wrong / Не знаю**: drops to box 1, `next_review_date = today + 1`.
- **Session**: due cards (`next_review_date <= today`), ordered by `next_review_date ASC, current_box ASC, created_at ASC`. User picks cap N ∈ {10, 15, 20} at session start.
- **No same-session relearn.** Skipped days just accumulate due cards.

---

## Deployment Architecture

```
Local machine          GitHub                DigitalOcean Droplet
─────────────          ──────                ────────────────────
.env (gitignored)      Secrets store:        Docker container
  BOT_TOKEN              BOT_TOKEN             env vars injected
  DB_PATH                DB_PATH               at deploy time
  DEFAULT_TIMEZONE       DEFAULT_TIMEZONE
                         SSH_HOST            ./storage/kartuli.db
                         SSH_USERNAME          (persistent volume)
                         SSH_PRIVATE_KEY
```

### CI/CD Flow (`.github/workflows/deploy.yml`)

1. **Trigger**: push to `main` or PR targeting `main`
2. **test job**: checkout → Python 3.11 → `pip install -e .` → `make test`
3. **deploy job** (only on push to `main`, after test passes):
   - SSH into droplet via `appleboy/ssh-action`
   - Secrets passed as env vars to SSH session via `envs:` parameter
   - On server: `git pull origin main && docker-compose up -d --build`
   - Docker Compose reads `BOT_TOKEN`, `DB_PATH`, `DEFAULT_TIMEZONE` from shell environment

### Docker

- **Image**: `python:3.11-slim`. Bakes in `src/`, `migrations/`, `data/`, `skills/`.
- **Volume**: `./storage:/app/storage` — persists SQLite database across rebuilds.
- **`DB_PATH`** must be `/app/storage/kartuli.db` in production.
- No `.env` file on the server — secrets come from GitHub Actions at deploy time.

---

## Adding a New Handler

1. Create `src/kartuli_bot/handlers/<name>.py` with a `router = Router()`.
2. Register it in `main.py`: `dp.include_router(handlers.<name>.router)`.
3. Add any new DB methods to `db.py`.
4. Add tests in `tests/`.

## Adding a Migration

Create `migrations/NNN_description.sql` (next number in sequence). It runs automatically on next startup.
