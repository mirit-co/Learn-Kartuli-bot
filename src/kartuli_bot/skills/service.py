import json

from ..db import Database
from .registry import SKILLS


class SkillService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def list_for_user(self, user_id: int) -> list[dict]:
        rows = self.db.get_skill_configs(user_id)
        result: list[dict] = []
        for row in rows:
            definition = SKILLS.get(row["skill_name"])
            result.append(
                {
                    "name": row["skill_name"],
                    "version": row["skill_version"],
                    "phase": definition.phase if definition else "unknown",
                    "description": definition.description if definition else "",
                    "config": json.loads(row["config_json"]),
                }
            )
        return result

    def upgrade_for_user(self, user_id: int, skill_name: str, version: str) -> bool:
        if skill_name not in SKILLS:
            return False
        self.db.update_skill_config(user_id, skill_name, version)
        return True
