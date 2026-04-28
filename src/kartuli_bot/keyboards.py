from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


SESSION_SIZE_OPTIONS: tuple[int, ...] = (10, 15, 20)


def onboarding_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Начнём сегодня! 🚀", callback_data="onboard:today")],
            [InlineKeyboardButton(text="Начну завтра", callback_data="onboard:tomorrow")],
        ]
    )


def review_keyboard(card_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Не знаю", callback_data=f"skip:{card_id}")]
        ]
    )


def session_size_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=str(n), callback_data=f"size:{n}")
                for n in SESSION_SIZE_OPTIONS
            ]
        ]
    )
