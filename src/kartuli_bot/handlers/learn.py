import re
import unicodedata

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from ..db import Database
from ..keyboards import session_config_keyboard, skip_keyboard
from ..leitner import BOX_LABELS

router = Router()


class ReviewSession(StatesGroup):
    configuring = State()
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


def _format_config_text(
    due_per_box: dict[int, int], selected_per_box: dict[int, int]
) -> str:
    lines = ["📋 Session setup\n"]
    for box in sorted(due_per_box):
        due = due_per_box[box]
        if due <= 0:
            continue
        selected = selected_per_box.get(box, due)
        label = BOX_LABELS.get(box, f"box {box}")
        lines.append(f"Box {box} ({label}): {due} due → {selected} selected")
    total = sum(selected_per_box.get(b, due_per_box.get(b, 0)) for b in due_per_box)
    lines.append(f"\nTotal: {total} cards")
    lines.append("\nTap buttons to adjust, then press Start:")
    return "\n".join(lines)


async def _send_next_session_card(
    message: Message, db: Database, user_id: int, state: FSMContext
) -> None:
    data = await state.get_data()
    card_ids = data.get("session_card_ids", [])
    index = data.get("session_index", 0)

    while index < len(card_ids):
        card_id = card_ids[index]
        card = db.get_card_for_review(user_id, card_id)
        if card:
            break
        index += 1
    else:
        await state.clear()
        await message.answer(
            "Session complete!\n\n" + _format_session_summary(db, user_id)
        )
        return

    front = card["front_side"]
    translit = card["transliteration"]
    box = card["current_box"]
    total = len(card_ids)
    text = f"[{index + 1}/{total}] Box {box}\n\n{front}"
    if translit:
        text += f"\n({translit})"
    text += "\n\nНапиши перевод на русском:"

    await state.set_state(ReviewSession.waiting_for_answer)
    await state.update_data(card_id=int(card["id"]), session_index=index + 1)
    await message.answer(text, reply_markup=skip_keyboard(int(card["id"])))


@router.message(Command("learn"))
async def learn(message: Message, db: Database, default_timezone: str, state: FSMContext) -> None:
    if not message.from_user:
        return
    user_id = db.ensure_user(message.from_user.id, default_timezone)
    db.ensure_user_cards(user_id)
    due_per_box = db.get_due_counts_per_box(user_id)

    if not any(due_per_box.values()):
        await message.answer(
            "No cards due today. Great work!\n\n" + _format_session_summary(db, user_id)
        )
        return

    selected = dict(due_per_box)
    await state.set_state(ReviewSession.configuring)
    await state.update_data(due_per_box=due_per_box, selected_per_box=selected)

    text = _format_config_text(due_per_box, selected)
    await message.answer(text, reply_markup=session_config_keyboard(due_per_box, selected))


@router.callback_query(F.data.startswith("box:"), ReviewSession.configuring)
async def set_box_limit(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.data or not callback.message:
        return
    parts = callback.data.split(":")
    box = int(parts[1])
    limit = int(parts[2])

    data = await state.get_data()
    selected = {int(k): v for k, v in data.get("selected_per_box", {}).items()}
    due_per_box = {int(k): v for k, v in data.get("due_per_box", {}).items()}

    selected[box] = limit
    await state.update_data(selected_per_box=selected)

    text = _format_config_text(due_per_box, selected)
    await callback.message.edit_text(
        text, reply_markup=session_config_keyboard(due_per_box, selected)
    )
    await callback.answer()


@router.callback_query(F.data == "session:start", ReviewSession.configuring)
async def start_session(
    callback: CallbackQuery, db: Database, default_timezone: str, state: FSMContext
) -> None:
    if not callback.from_user or not callback.message:
        return
    user_id = db.ensure_user(callback.from_user.id, default_timezone)
    data = await state.get_data()
    selected = {int(k): v for k, v in data.get("selected_per_box", {}).items()}

    card_ids = db.get_session_card_ids(user_id, selected)
    if not card_ids:
        await callback.message.edit_text("No cards selected. Use /learn to start again.")
        await state.clear()
        await callback.answer()
        return

    total = len(card_ids)
    await callback.message.edit_text(f"Starting session with {total} cards...")
    await state.update_data(session_card_ids=card_ids, session_index=0)
    await callback.answer()
    await _send_next_session_card(callback.message, db, user_id, state)


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

    card = db.get_card_for_review(user_id, card_id)
    if not card:
        await _send_next_session_card(message, db, user_id, state)
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

    await _send_next_session_card(message, db, user_id, state)


@router.callback_query(F.data.startswith("skip:"))
async def skip_card(
    callback: CallbackQuery, db: Database, default_timezone: str, state: FSMContext
) -> None:
    if not callback.from_user or not callback.message or not callback.data:
        return
    user_id = db.ensure_user(callback.from_user.id, default_timezone)
    card_id = int(callback.data.split(":")[1])
    card = db.get_card_for_review(user_id, card_id)
    if card:
        db.review_card(user_id, card_id, was_correct=False)
        await callback.message.answer(
            f"Ответ: {card['front_side']} — {card['back_side']}\n\nКарточка вернулась в Box 1."
        )
    await callback.answer()
    await _send_next_session_card(callback.message, db, user_id, state)
