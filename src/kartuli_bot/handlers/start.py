from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from ..db import Database
from ..keyboards import onboarding_keyboard

router = Router()


def _plural_cards(n: int) -> str:
    """Russian plural form for the noun 'карточка' agreeing with `n`."""
    n_abs = abs(n)
    last_two = n_abs % 100
    if 11 <= last_two <= 14:
        return "карточек"
    last = n_abs % 10
    if last == 1:
        return "карточка"
    if 2 <= last <= 4:
        return "карточки"
    return "карточек"


@router.message(CommandStart())
async def start(message: Message, db: Database, default_timezone: str) -> None:
    if not message.from_user:
        return
    db.ensure_user(message.from_user.id, default_timezone)
    card_count = db.count_base_deck_cards()
    cards_word = _plural_cards(card_count)
    await message.answer(
        "🇬🇪 Kartuli — учим грузинский каждый день\n"
        "\n"
        f"Здесь {card_count} {cards_word} уровня A1: "
        "алфавит, числа, фразы для магазина, рынка, "
        "транспорта, аптеки, общения с незнакомыми и "
        "оформления документов.\n"
        "\n"
        "📖 Метод — система Лейтнера (интервальное "
        "повторение):\n"
        "• Новые и забытые слова — каждый день\n"
        "• Запомнили — карточка уходит на повтор через "
        "2, 7, 14, а потом 30 дней\n"
        "• Ошиблись — карточка возвращается в начало\n"
        "\n"
        "Каждый день вы выбираете сколько карточек "
        "хотите изучить и повторить. Есть выбор 10, 15 "
        "или 20.\n"
        "\n"
        "Приятного изучения!",
        reply_markup=onboarding_keyboard(),
    )


@router.callback_query(F.data == "onboard:today")
async def onboard_today(callback: CallbackQuery, db: Database, default_timezone: str) -> None:
    if not callback.from_user or not callback.message:
        return
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()
    user_id = db.ensure_user(callback.from_user.id, default_timezone)
    db.ensure_user_cards(user_id)
    await callback.message.answer("Отлично, поехали! Жми /learn 🚀")


@router.callback_query(F.data == "onboard:tomorrow")
async def onboard_tomorrow(callback: CallbackQuery, db: Database, default_timezone: str) -> None:
    if not callback.from_user or not callback.message:
        return
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()
    db.ensure_user(callback.from_user.id, default_timezone)
    await callback.message.answer("Хорошо! Напомню тебе завтра в 10:00 ☀️")
