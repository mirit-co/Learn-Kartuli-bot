from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def skip_keyboard(card_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Не знаю", callback_data=f"skip:{card_id}")]
        ]
    )
