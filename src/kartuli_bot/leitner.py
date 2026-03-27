from datetime import date, timedelta


BOX_INTERVALS_DAYS = {
    1: 1,
    2: 2,
    3: 7,
    4: 14,
    5: 30,
}

BOX_LABELS = {
    1: "daily",
    2: "every 2 days",
    3: "weekly",
    4: "every 2 weeks",
    5: "monthly",
}


def clamp_box(box: int) -> int:
    return max(1, min(5, box))


def next_box_after_review(current_box: int, was_correct: bool) -> int:
    if not was_correct:
        return 1
    return clamp_box(current_box + 1)


def next_review_date_for_box(box: int, from_date: date | None = None) -> date:
    start = from_date or date.today()
    interval = BOX_INTERVALS_DAYS[clamp_box(box)]
    return start + timedelta(days=interval)
