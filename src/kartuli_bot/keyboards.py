from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

SESSION_PRESETS = [10, 15, 20]


def onboarding_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Начнём сегодня! 🚀", callback_data="onboard:today")],
            [InlineKeyboardButton(text="Начну завтра", callback_data="onboard:tomorrow")],
        ]
    )


def skip_keyboard(card_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Не знаю", callback_data=f"skip:{card_id}")]
        ]
    )


def session_size_keyboard(total_available: int) -> InlineKeyboardMarkup:
    buttons: list[InlineKeyboardButton] = []
    for n in SESSION_PRESETS:
        if n <= total_available:
            buttons.append(
                InlineKeyboardButton(text=str(n), callback_data=f"session:{n}")
            )
    if not buttons:
        buttons.append(
            InlineKeyboardButton(
                text=str(total_available), callback_data=f"session:{total_available}"
            )
        )
    return InlineKeyboardMarkup(inline_keyboard=[buttons])
