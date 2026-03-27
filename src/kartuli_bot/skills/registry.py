from dataclasses import dataclass


@dataclass(frozen=True)
class SkillDefinition:
    name: str
    description: str
    default_version: str
    phase: str


SKILLS: dict[str, SkillDefinition] = {
    "vocabulary_curator": SkillDefinition(
        name="vocabulary_curator",
        description=(
            "Curates and sequences vocabulary cards. Alphabet is never taught "
            "as isolated letters — each letter card pairs the letter with a real "
            "word starting with it (letter + word + translation). Controls topic "
            "unlock order and manages the A1 curriculum path."
        ),
        default_version="1.1.0",
        phase="v1",
    ),
    "session_planner": SkillDefinition(
        name="session_planner",
        description=(
            "Plans each daily review session: controls how many cards to show, "
            "review order within a session, spacing between repeats, and "
            "when to introduce new cards versus review old ones."
        ),
        default_version="1.0.0",
        phase="v1",
    ),
    "answer_evaluator": SkillDefinition(
        name="answer_evaluator",
        description=(
            "Evaluates user recall via typed answers: the user types the Russian "
            "translation, the bot normalizes both strings and checks for a match. "
            "Accepts alternative forms (e.g. 'пакет' or 'сумка' for 'пакет/сумка'). "
            "For alphabet cards, accepts just the word part after ' — '."
        ),
        default_version="1.1.0",
        phase="v1",
    ),
    "daily_reminder": SkillDefinition(
        name="daily_reminder",
        description=(
            "Manages daily learning reminders: controls notification timing, "
            "snooze windows, and recovery behavior when the user misses a day."
        ),
        default_version="1.0.0",
        phase="v1",
    ),
    "deck_validator": SkillDefinition(
        name="deck_validator",
        description=(
            "Validates deck integrity before import: detects duplicate cards, "
            "missing translations, empty fields, and inconsistent "
            "transliterations to keep content quality high."
        ),
        default_version="1.0.0",
        phase="v1",
    ),
    "load_adjuster": SkillDefinition(
        name="load_adjuster",
        description=(
            "Dynamically adjusts daily card load based on user retention rate "
            "and streak length. Adds extra reviews for weak cards and reduces "
            "volume when the user is overwhelmed."
        ),
        default_version="0.1.0",
        phase="v2",
    ),
    "streak_coach": SkillDefinition(
        name="streak_coach",
        description=(
            "Generates motivational messages: streak-aware nudges, weekly "
            "goals, milestone celebrations, and gentle re-engagement prompts "
            "after missed days."
        ),
        default_version="0.1.0",
        phase="v2",
    ),
    "pronunciation_guide": SkillDefinition(
        name="pronunciation_guide",
        description=(
            "Controls pronunciation and transliteration support: decides hint "
            "depth, when to show/hide transliteration as the user progresses, "
            "and optional audio integration."
        ),
        default_version="0.1.0",
        phase="v2",
    ),
}
