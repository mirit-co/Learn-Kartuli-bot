from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ..db import Database
from ..skills.service import SkillService

router = Router()


@router.message(Command("skill"))
async def skill(message: Message, db: Database, default_timezone: str) -> None:
    if not message.from_user:
        return
    user_id = db.ensure_user(message.from_user.id, default_timezone)
    service = SkillService(db)
    parts = (message.text or "").strip().split()
    if len(parts) == 3:
        skill_name = parts[1]
        version = parts[2]
        updated = service.upgrade_for_user(user_id, skill_name, version)
        if not updated:
            await message.answer("Unknown skill name.")
            return
        await message.answer(f"Updated {skill_name} to version {version}.")
        return
    if len(parts) != 1:
        await message.answer("Usage: /skill or /skill <name> <version>")
        return
    skills = service.list_for_user(user_id)
    lines = ["Your skills:\n"]
    for item in skills:
        lines.append(f"<b>{item['name']}</b> v{item['version']} ({item['phase']})")
        lines.append(f"  {item['description']}\n")
    lines.append("Upgrade: /skill <name> <version>")
    await message.answer("\n".join(lines))
