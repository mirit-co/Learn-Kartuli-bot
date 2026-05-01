from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    bot_token: str
    db_path: str
    default_timezone: str
    admin_telegram_id: int | None


def load_settings() -> Settings:
    load_dotenv()
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise ValueError("BOT_TOKEN is required in environment.")

    db_path = os.getenv("DB_PATH", "kartuli.db").strip()
    default_timezone = os.getenv("DEFAULT_TIMEZONE", "Europe/Tbilisi").strip()

    admin_id_raw = os.getenv("ADMIN_TELEGRAM_ID", "").strip()
    admin_telegram_id = int(admin_id_raw) if admin_id_raw.isdigit() else None

    # Keep DB path absolute to avoid cwd surprises in production.
    db_path_absolute = str(Path(db_path).expanduser().resolve())
    return Settings(
        bot_token=bot_token,
        db_path=db_path_absolute,
        default_timezone=default_timezone,
        admin_telegram_id=admin_telegram_id,
    )
