from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from aiogram import Bot

from .db import Database


async def reminder_loop(bot: Bot, db: Database) -> None:
    while True:
        now_utc = datetime.now(timezone.utc)
        due_users = db.get_users_due_for_reminder(now_utc)
        for item in due_users:
            due_count = db.get_due_count(item["user_id"])
            text = (
                "Давай поучим новые слова! 🇬🇪\n"
                f"Карточек на сегодня: {due_count}\n"
                "Жми /learn — начнём!"
            )
            try:
                await bot.send_message(chat_id=item["telegram_id"], text=text)
                db.mark_reminder_sent(item["user_id"], item["local_date"])
            except Exception:
                # Keep scheduler resilient; failed sends are retried next minute.
                continue
        await asyncio.sleep(60)
