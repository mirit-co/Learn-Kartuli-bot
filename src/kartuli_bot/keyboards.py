from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

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
            [
                InlineKeyboardButton(text="Показать пример", callback_data=f"hint:{card_id}"),
                InlineKeyboardButton(text="Не знаю", callback_data=f"skip:{card_id}"),
            ]
        ]
    )
