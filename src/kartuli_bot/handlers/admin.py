from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ..db import Database

router = Router()


@router.message(Command("admin"))
async def admin_stats(message: Message, db: Database, admin_telegram_id: int | None) -> None:
    if not message.from_user:
        return
    if admin_telegram_id is None or message.from_user.id != admin_telegram_id:
        return

    s = db.get_admin_stats()

    daily_lines = "\n".join(
        f"  {day}: +{cnt}" for day, cnt in s["new_by_day"]
    ) or "  нет данных"

    await message.answer(
        f"Всего пользователей: {s['total_users']}\n"
        f"Новых сегодня: {s['new_today']} | вчера: {s['new_yesterday']}\n"
        "\n"
        f"Активных сегодня (DAU): {s['dau_today']}\n"
        f"Активных вчера: {s['dau_yesterday']}\n"
        "\n"
        f"Повторений сегодня: {s['reviews_today']}\n"
        f"Повторений вчера: {s['reviews_yesterday']}\n"
        "\n"
        "Новые за 7 дней:\n"
        f"{daily_lines}"
    )
