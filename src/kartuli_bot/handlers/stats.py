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
    box_distribution = db.get_box_distribution(user_id)
    box5_stable_30d = db.get_box5_stable_30d_count(user_id)
    avg_by_topic = db.get_avg_days_box1_to_box5_by_topic(user_id)
    reviewed = summary["reviewed"]
    accuracy = int((summary["remembered"] / reviewed) * 100) if reviewed else 0
    box_lines = []
    for box in range(1, 6):
        box_lines.append(f"  Коробка {box}: {box_distribution.get(box, 0)}")
    avg_lines = ["  пока нет завершённых циклов"]
    if avg_by_topic:
        avg_lines = [f"  {topic}: {days} дн." for topic, days in avg_by_topic.items()]
    await message.answer(
        "Прогресс обучения:\n"
        f"- Повторено сегодня: {reviewed}\n"
        f"- Запомнила: {summary['remembered']}\n"
        f"- Забыла: {summary['forgot']}\n"
        f"- Точность сегодня: {accuracy}%\n"
        f"- К повторению сейчас: {due_now}\n"
        f"- В коробке 5 уже 30+ дней: {box5_stable_30d}\n\n"
        "Карточки по коробкам:\n"
        + "\n".join(box_lines)
        + "\n\nСреднее время от коробки 1 до коробки 5 по темам:\n"
        + "\n".join(avg_lines)
    )
