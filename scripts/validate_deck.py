from pathlib import Path
import sys

from kartuli_bot.deck_quality import load_deck, validate_deck


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    deck_path = root / "data" / "decks" / "a1_seed.json"
    deck = load_deck(str(deck_path))
    errors = validate_deck(deck)
    if errors:
        print("Deck validation failed:")
        for err in errors:
            print(f"- {err}")
        return 1
    print(f"Deck validation passed. Cards: {len(deck)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
