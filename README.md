# Kartuli SRS Bot

Telegram bot for learning Georgian vocabulary with a strict Spaced Repetition System (SRS).
Source of truth for the learning mechanics is [`task.md`](./task.md); this README is a short
operator-level summary aligned with the current code.

## Current Features

- `/start` onboarding and user creation
- `/learn` due-only session with a daily cap (10 / 15 / 20) chosen each run via inline buttons
- `/add` add your own lexical unit as `ka — ru` or `ru — ka`
- `/today` dashboard with day stats
- `/stats` SRS progress (today + box distribution + Box 5 stable)
- `/settings` and `/settings HH:MM Area/City` for reminders
- `/reminder_on` and `/reminder_off`
- `/skill` and `/skill <skill_name> <version>` for skill versions
- SRS boxes with intervals: 1, 2, 7, 14, 30 days
- Binary typed-answer evaluation (`correct` / `wrong`) with deterministic normalization and 1-char Levenshtein tolerance for targets ≥ 4 chars
- In-session button: `Не знаю` (= `wrong`); transliteration shows passively under the prompt
- User-added pair is split into two cards (KA→RU tomorrow, RU→KA day after tomorrow)
- Duplicate protection for user-added cards
- SQLite persistence
- A1 seed deck with alphabet + practical topics

## How the SRS Works

Strictly the rules from `task.md` §2–§5. No "almost correct", no same-session relearn,
no hint ladder.

- **Boxes & intervals**: `1d → 2d → 7d → 14d → 30d`. Box 5 stays at 30 days.
- **Outcomes are binary**: `correct` promotes one box (5 stays 5); `wrong` (or `Не знаю`)
  drops the card straight to Box 1 with `next_review_date = today + 1`, regardless of
  the previous box.
- **Daily session = capped slice of the due queue**: every card with
  `next_review_date <= today`, ordered by `next_review_date ASC, current_box ASC,
  created_at ASC`, then the user picks `N ∈ {10, 15, 20}` at the start of `/learn`
  and the session runs over the first `min(N, total_due)` cards. The rest stay due
  for the next run. A card is shown at most once per session; if you miss it, it
  appears tomorrow.
- **Skipped days don't burn cards** — due cards just accumulate.
- **One lexical unit → two independent cards**: KA→RU (recognition) and RU→KA
  (production). Each has its own box and review date. Currently full pairing applies
  to `/add` cards; the curated A1 seed is KA→RU only (RU→KA seed pairing is in roadmap).
- **Hints don't change grading**: `transliteration` is shown passively under the
  prompt before the answer. `example_ka` / `example_ru` are stored on cards but not
  shown in the UI yet — the in-session hint button was removed because the curated
  deck has no examples filled in. It will return when the seed is enriched.

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

---

## Deployment (DigitalOcean + GitHub Actions)

Secrets are stored in **GitHub Secrets only** — no `.env` on the server.
Local development uses a `.env` file (gitignored).

### First-time server setup

**1. Create SSH deploy key** (on your Mac):
```bash
ssh-keygen -t ed25519 -C "kartuli-bot-deploy" -f ~/.ssh/kartuli_bot_deploy
cat ~/.ssh/kartuli_bot_deploy.pub | pbcopy   # copy public key
```

**2. Create DigitalOcean Droplet**
- Ubuntu 24.04 LTS, Basic $6/mo (1 vCPU, 1 GB RAM)
- During creation: Authentication → SSH Keys → New SSH Key → paste the public key

**3. Connect to the server** (on your Mac):
```bash
ssh -i ~/.ssh/kartuli_bot_deploy root@<IP>
```
First connection will ask `Are you sure you want to continue connecting (yes/no)?` — type `yes`.

**4. Install Docker** (on the server):
```bash
apt update && apt upgrade -y
```
After upgrade you may see a message about a new kernel — reboot to apply it:
```bash
reboot
```
Reconnect after ~30 seconds, then install Docker:
```bash
ssh -i ~/.ssh/kartuli_bot_deploy root@<IP>
apt install -y docker.io docker-compose-v2 git
systemctl enable --now docker
```
Verify:
```bash
docker --version
docker compose version
```

**5. Add a GitHub SSH key to the server** (so git can clone the private repo):
```bash
ssh-keygen -t ed25519 -C "digitalocean-kartuli" -f ~/.ssh/id_ed25519
cat ~/.ssh/id_ed25519.pub
```
Copy the output, then add it in GitHub:
**github.com → Settings → SSH and GPG keys → New SSH key** → paste → Save.

**6. Clone the repository** (on the server):
```bash
git clone git@github.com:mirit-co/Learn-Kartuli-bot.git ~/kartuli-bot
cd ~/kartuli-bot && mkdir -p storage
```

**7. First manual run** (before CI/CD is wired up):
```bash
BOT_TOKEN=<token> \
DB_PATH=/app/storage/kartuli.db \
DEFAULT_TIMEZONE=Europe/Tbilisi \
docker-compose up -d --build
```

Verify: `docker compose logs -f` — should show polling started. Test with `/start` in Telegram.
Exit logs with `Ctrl+C`, disconnect from server with `exit`.

### GitHub Secrets

Add in **Settings → Secrets and variables → Actions**:

| Secret | Value |
|--------|-------|
| `SSH_HOST` | Droplet IP |
| `SSH_USERNAME` | `root` |
| `SSH_PRIVATE_KEY` | contents of `~/.ssh/kartuli_bot_deploy` (private key, on your Mac) |
| `BOT_TOKEN` | Telegram bot token |
| `DB_PATH` | `/app/storage/kartuli.db` |
| `DEFAULT_TIMEZONE` | `Europe/Tbilisi` |

Copy private key to clipboard (on your Mac): `cat ~/.ssh/kartuli_bot_deploy | pbcopy`

### After setup

Every push/merge to `main`:
1. GitHub Actions runs `make test`
2. On success: SSH into droplet → `git pull` → `docker-compose up -d --build`
3. Secrets are injected as env vars — no `.env` file needed on server
