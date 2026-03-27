from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from zoneinfo import ZoneInfo

from ..db import Database

router = Router()


def _is_valid_hhmm(value: str) -> bool:
    parts = value.split(":")
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        return False
    hh, mm = int(parts[0]), int(parts[1])
    return 0 <= hh <= 23 and 0 <= mm <= 59


@router.message(Command("settings"))
async def settings(message: Message, db: Database, default_timezone: str) -> None:
    if not message.from_user:
        return
    user_id = db.ensure_user(message.from_user.id, default_timezone)
    parts = (message.text or "").strip().split()
    if len(parts) == 3:
        reminder_time = parts[1]
        timezone = parts[2]
        if not _is_valid_hhmm(reminder_time):
            await message.answer("Invalid time format. Use /settings HH:MM Area/City")
            return
        try:
            ZoneInfo(timezone)
        except (KeyError, ValueError):
            await message.answer("Invalid timezone. Example: Europe/Tbilisi")
            return
        db.update_reminder_settings(user_id, reminder_time=reminder_time, timezone=timezone)
    elif len(parts) != 1:
        await message.answer("Usage: /settings or /settings HH:MM Area/City")
        return

    due = db.get_due_count(user_id)
    reminder = db.get_reminder_settings(user_id)
    await message.answer(
        "Settings:\n"
        f"Reminder: {'on' if int(reminder['enabled']) else 'off'}\n"
        f"Time: {reminder['reminder_time']}\n"
        f"Timezone: {reminder['timezone']}\n"
        f"Due now: {due}"
    )


@router.message(Command("reminder_on"))
async def reminder_on(message: Message, db: Database, default_timezone: str) -> None:
    if not message.from_user:
        return
    user_id = db.ensure_user(message.from_user.id, default_timezone)
    db.update_reminder_settings(user_id, enabled=True)
    await message.answer("Daily reminders are enabled.")


@router.message(Command("reminder_off"))
async def reminder_off(message: Message, db: Database, default_timezone: str) -> None:
    if not message.from_user:
        return
    user_id = db.ensure_user(message.from_user.id, default_timezone)
    db.update_reminder_settings(user_id, enabled=False)
    await message.answer("Daily reminders are disabled.")
