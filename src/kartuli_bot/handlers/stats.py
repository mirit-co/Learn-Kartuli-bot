from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ..db import Database

router = Router()


@router.message(Command("stats"))
async def stats(message: Message, db: Database, default_timezone: str) -> None:
    if not message.from_user:
        return
    user_id = db.ensure_user(message.from_user.id, default_timezone)
    summary = db.get_today_review_stats(user_id)
    due_now = db.get_due_count(user_id)
    due_tomorrow = db.get_due_tomorrow_count(user_id)
    await message.answer(
        "Progress snapshot:\n"
        f"- Reviewed today: {summary['reviewed']}\n"
        f"- Remembered: {summary['remembered']}\n"
        f"- Forgot: {summary['forgot']}\n"
        f"- Due now: {due_now}\n"
        f"- Due tomorrow: {due_tomorrow}"
    )
