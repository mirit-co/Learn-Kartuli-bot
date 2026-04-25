import re
from html import escape as html_escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from ..db import Database

router = Router()

_GEORGIAN_RE = re.compile(r"[\u10A0-\u10FF]")
_CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")
_PAIR_SPLIT_RE = re.compile(r"\s*(?:—|–|-)\s*")


class AddCardFlow(StatesGroup):
    waiting_for_pair = State()
    waiting_for_confirm = State()


def _parse_pair(raw: str) -> tuple[str, str] | None:
    parts = _PAIR_SPLIT_RE.split(raw.strip(), maxsplit=1)
    if len(parts) != 2:
        return None
    left = parts[0].strip()
    right = parts[1].strip()
    if not left or not right:
        return None
    left_has_ka = bool(_GEORGIAN_RE.search(left))
    right_has_ka = bool(_GEORGIAN_RE.search(right))
    left_has_ru = bool(_CYRILLIC_RE.search(left))
    right_has_ru = bool(_CYRILLIC_RE.search(right))
    if left_has_ka and right_has_ru:
        return left, right
    if left_has_ru and right_has_ka:
        return right, left
    return None


def _confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Сохранить", callback_data="add:confirm"),
                InlineKeyboardButton(text="Отмена", callback_data="add:cancel"),
            ]
        ]
    )


@router.message(Command("add"))
async def add_card(message: Message, db: Database, default_timezone: str, state: FSMContext) -> None:
    if not message.from_user:
        return
    user_id = db.ensure_user(message.from_user.id, default_timezone)
    db.ensure_user_cards(user_id)

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) == 1:
        await state.set_state(AddCardFlow.waiting_for_pair)
        await message.answer(
            "Пришли фразу в формате `ka — ru` или `ru — ka`.\n"
            "Пример: `რამდენი ღირს? — сколько стоит?`"
        )
        return

    pair = _parse_pair(parts[1])
    if not pair:
        await message.answer(
            "Не смогла распознать пару. Используй грузинский и русский текст через тире: `ka — ru`."
        )
        return
    ka_text, ru_text = pair
    await state.set_state(AddCardFlow.waiting_for_confirm)
    await state.update_data(add_ka=ka_text, add_ru=ru_text)
    await message.answer(
        "Проверь карточку перед сохранением:\n\n"
        f"KA: {html_escape(ka_text)}\n"
        f"RU: {html_escape(ru_text)}\n\n"
        "Создам две карточки в Box 1:\n"
        "- KA→RU на завтра\n"
        "- RU→KA на послезавтра",
        reply_markup=_confirm_keyboard(),
    )


@router.message(AddCardFlow.waiting_for_pair)
async def add_card_waiting_pair(
    message: Message, db: Database, default_timezone: str, state: FSMContext
) -> None:
    if not message.from_user or not message.text:
        return
    db.ensure_user(message.from_user.id, default_timezone)
    pair = _parse_pair(message.text)
    if not pair:
        await message.answer(
            "Формат не распознан. Попробуй так: `ხორცი — мясо` или `мясо — ხორცი`."
        )
        return
    ka_text, ru_text = pair
    await state.set_state(AddCardFlow.waiting_for_confirm)
    await state.update_data(add_ka=ka_text, add_ru=ru_text)
    await message.answer(
        "Проверь карточку перед сохранением:\n\n"
        f"KA: {html_escape(ka_text)}\n"
        f"RU: {html_escape(ru_text)}\n\n"
        "Создам две карточки в Box 1:\n"
        "- KA→RU на завтра\n"
        "- RU→KA на послезавтра",
        reply_markup=_confirm_keyboard(),
    )


@router.callback_query(F.data.in_({"add:confirm", "add:cancel"}), AddCardFlow.waiting_for_confirm)
async def add_card_confirm(
    callback: CallbackQuery, db: Database, default_timezone: str, state: FSMContext
) -> None:
    if not callback.from_user or not callback.message or not callback.data:
        return
    await callback.message.edit_reply_markup(reply_markup=None)
    if callback.data == "add:cancel":
        await state.clear()
        await callback.answer("Отменено")
        await callback.message.answer("Не сохранила карточку.")
        return

    user_id = db.ensure_user(callback.from_user.id, default_timezone)
    data = await state.get_data()
    ka_text = str(data.get("add_ka", "")).strip()
    ru_text = str(data.get("add_ru", "")).strip()
    if not ka_text or not ru_text:
        await state.clear()
        await callback.answer()
        await callback.message.answer("Не нашла данные карточки, попробуй /add снова.")
        return

    try:
        db.add_user_lexical_unit(
            user_id=user_id,
            ka_text=ka_text,
            ru_text=ru_text,
            transliteration=None,
            example_ka=None,
            example_ru=None,
            topic="other",
        )
    except ValueError as exc:
        await state.clear()
        await callback.answer()
        if str(exc) == "duplicate_lexical_unit":
            await callback.message.answer(
                "Такая лексическая единица уже есть. Не добавила дубликат."
            )
        else:
            await callback.message.answer("Не удалось сохранить карточку.")
        return

    await state.clear()
    await callback.answer("Сохранено")
    await callback.message.answer(
        "Готово. Добавила 2 карточки:\n"
        "- KA→RU (появится завтра)\n"
        "- RU→KA (появится послезавтра)"
    )
