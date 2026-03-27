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
        "Welcome to Kartuli Leitner Bot.\n"
        "Commands:\n"
        "- /learn daily review\n"
        "- /today due + session summary\n"
        "- /stats progress snapshot\n"
        "- /settings [HH:MM Area/City]\n"
        "- /skill [skill_name version]"
    )
