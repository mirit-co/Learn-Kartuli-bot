from dataclasses import dataclass


@dataclass(frozen=True)
class SkillDefinition:
    name: str
    description: str
    default_version: str
    phase: str


SKILLS: dict[str, SkillDefinition] = {
    "vocabulary_curator_a1": SkillDefinition(
        name="vocabulary_curator_a1",
        description=(
            "Curates A1 vocabulary content by topic and keeps the alphabet flow "
            "as letter + anchor word. Produces card content fields such as "
            "transliteration and examples."
        ),
        default_version="1.0.0",
        phase="v1",
    ),
    "srs_engine": SkillDefinition(
        name="srs_engine",
        description=(
            "Implements strict SRS logic: 5 boxes, binary outcomes, due-only "
            "queue ordering, and next review date calculations."
        ),
        default_version="1.0.0",
        phase="v1",
    ),
    "answer_evaluator_ru_ka": SkillDefinition(
        name="answer_evaluator_ru_ka",
        description=(
            "Evaluates typed answers with deterministic normalization and binary "
            "correct/wrong output, including a small typo tolerance threshold."
        ),
        default_version="1.0.0",
        phase="v1",
    ),
    "session_runner": SkillDefinition(
        name="session_runner",
        description=(
            "Runs review sessions card-by-card using due-only queues and delegates "
            "grading to answer evaluator and box updates to SRS engine."
        ),
        default_version="1.0.0",
        phase="v1",
    ),
    "telegram_ux": SkillDefinition(
        name="telegram_ux",
        description=(
            "Controls Telegram interaction layer: reminder settings, in-session "
            "buttons, and progress snapshots in SRS terms."
        ),
        default_version="1.0.0",
        phase="v1",
    ),
    "card_intake": SkillDefinition(
        name="card_intake",
        description=(
            "Accepts user-provided lexical units from real-life situations and "
            "creates paired KA→RU and RU→KA cards in Box 1."
        ),
        default_version="1.0.0",
        phase="v1",
    ),
}
