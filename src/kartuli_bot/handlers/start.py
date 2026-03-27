from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from ..db import Database

router = Router()


@router.message(CommandStart())
async def start(message: Message, db: Database, default_timezone: str) -> None:
    if not message.from_user:
        return
    db.ensure_user(message.from_user.id, default_timezone)
    await message.answer(
        "🇬🇪 Kartuli — учим грузинский каждый день\n"
        "\n"
        "Здесь 111 карточек уровня A1: алфавит, "
        "числа, фразы для магазина, рынка, транспорта "
        "и повседневного общения.\n"
        "\n"
        "📖 Метод — система Лейтнера (интервальное повторение):\n"
        "• Новые и забытые слова — каждый день\n"
        "• Запомнил — карточка уходит на повтор через "
        "2, 7, 14, а потом 30 дней\n"
        "• Ошибся — карточка возвращается в начало\n"
        "\n"
        "🗓 Что делать каждый день:\n"
        "1. Нажми /learn — бот покажет все карточки на сегодня\n"
        "2. Напиши перевод или нажми «Не знаю»\n"
        "3. 5–10 минут в день — и через пару месяцев "
        "заговоришь на базовом уровне\n"
        "\n"
        "Команды:\n"
        "/learn — начать повторение\n"
        "/today — сколько карточек на сегодня\n"
        "/stats — прогресс по коробкам\n"
        "/settings HH:MM — напоминание на каждый день\n"
        "/skill — навыки курса"
    )
