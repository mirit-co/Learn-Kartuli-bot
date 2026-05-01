from __future__ import annotations

import asyncio
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, MenuButtonCommands

from .config import load_settings
from .db import Database
from .handlers.add import router as add_router
from .handlers.admin import router as admin_router
from .handlers.learn import router as learn_router
from .handlers.skill import router as skill_router
from .handlers.settings import router as settings_router
from .handlers.start import router as start_router
from .handlers.stats import router as stats_router
from .scheduler import reminder_loop


def build_db() -> Database:
    root = Path(__file__).resolve().parents[2]
    settings = load_settings()
    return Database(
        db_path=settings.db_path,
        migrations_dir=str(root / "migrations"),
        deck_path=str(root / "data" / "decks" / "a1_seed.json"),
    )


async def main() -> None:
    settings = load_settings()
    db = build_db()
    db.initialize()

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp["db"] = db
    dp["default_timezone"] = settings.default_timezone
    dp["admin_telegram_id"] = settings.admin_telegram_id

    dp.include_router(admin_router)
    dp.include_router(start_router)
    dp.include_router(add_router)
    dp.include_router(learn_router)
    dp.include_router(skill_router)
    dp.include_router(settings_router)
    dp.include_router(stats_router)

    await bot.set_my_commands([
        BotCommand(command="start", description="Начать / о боте"),
        BotCommand(command="learn", description="Учить слова"),
        BotCommand(command="add", description="Добавить своё слово/фразу"),
    ])
    await bot.set_chat_menu_button(menu_button=MenuButtonCommands())

    scheduler_task = asyncio.create_task(reminder_loop(bot, db))
    try:
        await dp.start_polling(bot)
    finally:
        scheduler_task.cancel()


if __name__ == "__main__":
    asyncio.run(main())
