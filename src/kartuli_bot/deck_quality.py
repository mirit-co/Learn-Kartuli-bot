import json
from pathlib import Path


REQUIRED_KEYS = {"front_side", "back_side", "topic", "transliteration"}


def load_deck(path: str) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_deck(deck: list[dict]) -> list[str]:
    errors: list[str] = []
    seen_front: set[str] = set()
    for index, card in enumerate(deck):
        missing = REQUIRED_KEYS - set(card.keys())
        if missing:
            errors.append(f"Card #{index} is missing keys: {sorted(missing)}")
        front = str(card.get("front_side", "")).strip()
        back = str(card.get("back_side", "")).strip()
        topic = str(card.get("topic", "")).strip()
        translit = str(card.get("transliteration", "")).strip()
        if not front or not back or not topic:
            errors.append(f"Card #{index} has empty required values.")
        if len(translit) == 0:
            errors.append(f"Card #{index} has empty transliteration.")
        front_key = front.lower()
        if front_key in seen_front:
            errors.append(f"Duplicate front_side found: {front}")
        seen_front.add(front_key)
    return errors
