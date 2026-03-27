import re
import unicodedata

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from ..db import Database
from ..keyboards import skip_keyboard

router = Router()


class ReviewSession(StatesGroup):
    waiting_for_answer = State()


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"[^\w\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _accepted_answers(back_side: str) -> list[str]:
    """Build a list of accepted answer variants from the back_side text.

    For alphabet cards like 'а (a) — ананас', accepts both the full text
    and just the word part after ' — '. Also splits on '/' for alternatives
    like 'пакет/сумка'.
    """
    variants: list[str] = [back_side]
    if " — " in back_side:
        variants.append(back_side.split(" — ", 1)[1])
    expanded: list[str] = []
    for v in variants:
        if "/" in v:
            expanded.extend(v.split("/"))
        expanded.append(v)
    return [_normalize(v) for v in expanded if _normalize(v)]


def _format_session_summary(db: Database, user_id: int) -> str:
    stats = db.get_today_review_stats(user_id)
    due_tomorrow = db.get_due_tomorrow_count(user_id)
    reviewed = stats["reviewed"]
    remembered = stats["remembered"]
    remember_rate = int((remembered / reviewed) * 100) if reviewed else 0
    return (
        "Session summary:\n"
        f"- Reviewed: {reviewed}\n"
        f"- Remembered: {remembered}\n"
        f"- Remember rate: {remember_rate}%\n"
        f"- Due tomorrow: {due_tomorrow}"
    )


async def _send_next_due(message: Message, db: Database, user_id: int, state: FSMContext) -> None:
    due_card = db.get_due_card(user_id)
    if not due_card:
        await state.clear()
        await message.answer(
            "No cards due today. Great work!\n\n" + _format_session_summary(db, user_id)
        )
        return
    front = due_card["front_side"]
    translit = due_card["transliteration"]
    box = due_card["current_box"]
    text = f"Box {box}\n\n{front}"
    if translit:
        text += f"\n({translit})"
    text += "\n\nНапиши перевод на русском:"
    await state.set_state(ReviewSession.waiting_for_answer)
    await state.update_data(card_id=int(due_card["id"]))
    await message.answer(text, reply_markup=skip_keyboard(int(due_card["id"])))


@router.message(Command("learn"))
async def learn(message: Message, db: Database, default_timezone: str, state: FSMContext) -> None:
    if not message.from_user:
        return
    user_id = db.ensure_user(message.from_user.id, default_timezone)
    db.ensure_user_cards(user_id)
    await _send_next_due(message, db, user_id, state)


@router.message(Command("today"))
async def today(message: Message, db: Database, default_timezone: str) -> None:
    if not message.from_user:
        return
    user_id = db.ensure_user(message.from_user.id, default_timezone)
    db.ensure_user_cards(user_id)
    due_count = db.get_due_count(user_id)
    await message.answer(f"Cards due today: {due_count}\n\n{_format_session_summary(db, user_id)}")


@router.message(ReviewSession.waiting_for_answer)
async def check_answer(
    message: Message, db: Database, default_timezone: str, state: FSMContext
) -> None:
    if not message.from_user or not message.text:
        return
    user_id = db.ensure_user(message.from_user.id, default_timezone)
    data = await state.get_data()
    card_id = data.get("card_id")
    if card_id is None:
        await state.clear()
        return

    card = db.get_due_card_by_id(user_id, card_id)
    if not card:
        await _send_next_due(message, db, user_id, state)
        return

    user_answer = _normalize(message.text)
    accepted = _accepted_answers(card["back_side"])
    correct = user_answer in accepted

    if correct:
        db.review_card(user_id, card_id, was_correct=True)
        await message.answer(f"Правильно!\n\n{card['front_side']} — {card['back_side']}")
    else:
        db.review_card(user_id, card_id, was_correct=False)
        await message.answer(
            f"Неправильно.\n\n{card['front_side']} — {card['back_side']}\n\n"
            "Карточка вернулась в Box 1."
        )

    await _send_next_due(message, db, user_id, state)


@router.callback_query(F.data.startswith("skip:"))
async def skip_card(
    callback: CallbackQuery, db: Database, default_timezone: str, state: FSMContext
) -> None:
    if not callback.from_user or not callback.message or not callback.data:
        return
    user_id = db.ensure_user(callback.from_user.id, default_timezone)
    card_id = int(callback.data.split(":")[1])
    card = db.get_due_card_by_id(user_id, card_id)
    if card:
        db.review_card(user_id, card_id, was_correct=False)
        await callback.message.answer(
            f"Ответ: {card['front_side']} — {card['back_side']}\n\nКарточка вернулась в Box 1."
        )
    await callback.answer()
    await _send_next_due(callback.message, db, user_id, state)
