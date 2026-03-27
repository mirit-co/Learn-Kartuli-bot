import re
from html import escape as html_escape

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ..db import Database
from ..skills.service import SkillService

router = Router()

_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


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
        if not _VERSION_RE.match(version):
            await message.answer("Invalid version format. Use semver: X.Y.Z")
            return
        updated = service.upgrade_for_user(user_id, skill_name, version)
        if not updated:
            await message.answer("Unknown skill name.")
            return
        await message.answer(
            f"Updated {html_escape(skill_name)} to version {html_escape(version)}."
        )
        return
    if len(parts) != 1:
        await message.answer("Usage: /skill or /skill &lt;name&gt; &lt;version&gt;")
        return
    skills = service.list_for_user(user_id)
    lines = ["Your skills:\n"]
    for item in skills:
        name = html_escape(item["name"])
        version = html_escape(item["version"])
        phase = html_escape(item["phase"])
        desc = html_escape(item["description"])
        lines.append(f"<b>{name}</b> v{version} ({phase})")
        lines.append(f"  {desc}\n")
    lines.append("Upgrade: /skill &lt;name&gt; &lt;version&gt;")
    await message.answer("\n".join(lines))
