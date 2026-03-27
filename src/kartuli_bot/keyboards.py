from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def skip_keyboard(card_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Не знаю", callback_data=f"skip:{card_id}")]
        ]
    )


def _box_options(due: int) -> list[int]:
    if due <= 0:
        return []
    if due <= 5:
        return [0, due]
    if due <= 10:
        return [0, 5, due]
    if due <= 20:
        return [0, 5, 10, due]
    return [0, 5, 10, 20, due]


def session_config_keyboard(
    due_per_box: dict[int, int],
    selected_per_box: dict[int, int],
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for box in sorted(due_per_box):
        due = due_per_box[box]
        if due <= 0:
            continue
        options = _box_options(due)
        selected = selected_per_box.get(box, due)
        button_row: list[InlineKeyboardButton] = []
        for i, opt in enumerate(options):
            if opt == 0:
                label = "0"
            elif opt == due:
                label = f"All ({due})"
            else:
                label = str(opt)
            if i == 0:
                label = f"{box}: {label}"
            if opt == selected:
                label = f"✓ {label}"
            button_row.append(
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"box:{box}:{opt}",
                )
            )
        rows.append(button_row)

    total = sum(selected_per_box.get(b, due_per_box.get(b, 0)) for b in due_per_box)
    rows.append(
        [InlineKeyboardButton(text=f"▶ Start ({total} cards)", callback_data="session:start")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)
