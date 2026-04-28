import logging
import re
import unicodedata
from html import escape as html_escape
import json

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from ..db import Database
from ..keyboards import SESSION_SIZE_OPTIONS, review_keyboard, session_size_keyboard
from ..srs import BOX_LABELS

logger = logging.getLogger(__name__)

router = Router()


class ReviewSession(StatesGroup):
    waiting_for_answer = State()


def _normalize(text: str) -> str:
    text = text.replace("ё", "е").replace("Ё", "Е")
    text = text.lower().strip()
    text = unicodedata.normalize("NFC", text)
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"[.,;:!?\"'`]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            insertions = prev[j] + 1
            deletions = cur[j - 1] + 1
            substitutions = prev[j - 1] + (0 if ca == cb else 1)
            cur.append(min(insertions, deletions, substitutions))
        prev = cur
    return prev[-1]


def _accepted_answers(back_side: str, accepted_answers_json: str | None) -> list[str]:
    variants: list[str] = [back_side]
    if accepted_answers_json:
        try:
            raw = json.loads(accepted_answers_json)
            if isinstance(raw, list):
                variants.extend(str(x) for x in raw)
        except json.JSONDecodeError:
            logger.warning("Failed to parse accepted_answers_json: %s", accepted_answers_json)
    normalized = [_normalize(v) for v in variants if _normalize(v)]
    return list(dict.fromkeys(normalized))


def _is_correct_answer(user_text: str, accepted: list[str]) -> bool:
    if not accepted:
        return False
    normalized_user = _normalize(user_text)
    if normalized_user in accepted:
        return True
    for target in accepted:
        if len(target) >= 4 and _levenshtein(normalized_user, target) <= 1:
            return True
    return False


def _format_session_summary(db: Database, user_id: int) -> str:
    stats = db.get_today_review_stats(user_id)
    due_tomorrow = db.get_due_tomorrow_count(user_id)
    reviewed = stats["reviewed"]
    remembered = stats["remembered"]
    remember_rate = int((remembered / reviewed) * 100) if reviewed else 0
    return (
        "Итоги сессии:\n"
        f"- Повторено: {reviewed}\n"
        f"- Запомнила: {remembered}\n"
        f"- Процент: {remember_rate}%\n"
        f"- На завтра: {due_tomorrow}"
    )


def _format_due_overview(due_per_box: dict[int, int]) -> str:
    total_due = sum(due_per_box.values())
    lines = ["📋 Карточки на сегодня\n"]
    if total_due > 0:
        lines.append(f"К изучению: {total_due}")
        for box in sorted(due_per_box):
            count = due_per_box[box]
            if count <= 0:
                continue
            label = BOX_LABELS.get(box, f"коробка {box}")
            lines.append(f"  Коробка {box} ({label}): {count}")
    lines.append(
        "\nСколько карточек хочешь сегодня? Возьми порцию — остальное останется на завтра."
    )
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
            "Отличная работа, увидимся завтра! 🎉\n\n" + _format_session_summary(db, user_id)
        )
        return

    front = html_escape(card["front_side"])
    translit = html_escape(card["transliteration"] or "")
    box = card["current_box"]
    total = len(card_ids)
    text = f"[{index + 1}/{total}] Коробка {box}\n\n{front}"
    if translit:
        text += f"\n({translit})"
    text += "\n\nНапиши ответ:"

    await state.set_state(ReviewSession.waiting_for_answer)
    await state.update_data(card_id=int(card["id"]), session_index=index + 1)
    await message.answer(text, reply_markup=review_keyboard(int(card["id"])))


@router.message(Command("learn"))
async def learn(message: Message, db: Database, default_timezone: str, state: FSMContext) -> None:
    if not message.from_user:
        return
    await state.clear()
    user_id = db.ensure_user(message.from_user.id, default_timezone)
    db.ensure_user_cards(user_id)
    due_per_box = db.get_due_counts_per_box(user_id)
    total_due = sum(due_per_box.values())

    if total_due == 0:
        await message.answer(
            "На сегодня всё повторено. Молодец! 🎉\n\n" + _format_session_summary(db, user_id)
        )
        return

    await message.answer(
        _format_due_overview(due_per_box),
        reply_markup=session_size_keyboard(),
    )


@router.callback_query(F.data.startswith("size:"))
async def start_sized_session(
    callback: CallbackQuery, db: Database, default_timezone: str, state: FSMContext
) -> None:
    if not callback.from_user or not callback.message or not callback.data:
        return
    try:
        size = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer()
        return
    if size not in SESSION_SIZE_OPTIONS:
        await callback.answer()
        return

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()

    user_id = db.ensure_user(callback.from_user.id, default_timezone)
    db.ensure_user_cards(user_id)
    card_ids = db.get_session_card_ids_limited(user_id, size)
    if not card_ids:
        await callback.message.answer("Карточек пока нет. Запусти /learn ещё раз.")
        await state.clear()
        return

    total = len(card_ids)
    await callback.message.answer(f"Поехали — {total} карточек в сессии")
    await state.update_data(session_card_ids=card_ids, session_index=0)
    await _send_next_session_card(callback.message, db, user_id, state)


@router.message(Command("today"))
async def today(message: Message, db: Database, default_timezone: str) -> None:
    if not message.from_user:
        return
    user_id = db.ensure_user(message.from_user.id, default_timezone)
    db.ensure_user_cards(user_id)
    due_count = db.get_due_count(user_id)
    await message.answer(
        f"К изучению на сегодня: {due_count}\n\n{_format_session_summary(db, user_id)}"
    )


@router.message(ReviewSession.waiting_for_answer, F.text & ~F.text.startswith("/"))
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

    accepted = _accepted_answers(card["back_side"], card["accepted_answers_json"])
    correct = _is_correct_answer(message.text, accepted)

    front = html_escape(card["front_side"])
    back = html_escape(card["back_side"])
    if correct:
        db.review_card(user_id, card_id, was_correct=True)
        await message.answer(f"Правильно!\n\n{front} — {back}")
    else:
        db.review_card(user_id, card_id, was_correct=False)
        await message.answer(
            f"Неправильно.\n\n{front} — {back}\n\n"
            "Карточка вернулась в коробку 1."
        )

    await _send_next_session_card(message, db, user_id, state)


@router.callback_query(F.data.startswith("skip:"))
async def skip_card(
    callback: CallbackQuery, db: Database, default_timezone: str, state: FSMContext
) -> None:
    if not callback.from_user or not callback.message or not callback.data:
        return
    try:
        card_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer()
        return
    user_id = db.ensure_user(callback.from_user.id, default_timezone)
    card = db.get_card_for_review(user_id, card_id)
    if card:
        db.review_card(user_id, card_id, was_correct=False)
        front = html_escape(card["front_side"])
        back = html_escape(card["back_side"])
        await callback.message.answer(
            f"Ответ: {front} — {back}\n\nКарточка вернулась в коробку 1."
        )
    await callback.answer()
    await _send_next_session_card(callback.message, db, user_id, state)


