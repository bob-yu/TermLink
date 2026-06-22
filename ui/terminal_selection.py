from typing import Callable, Optional, Tuple


Cell = Tuple[int, int]
Selection = Tuple[Cell, Cell]


def is_word_char(char: str) -> bool:
    return char.isalnum() or char in "_-."


def normalize_selection(start: Cell, end: Cell) -> Selection:
    if start > end:
        return end, start
    return start, end


def is_cell_selected(
    row: int,
    col: int,
    start: Optional[Cell],
    end: Optional[Cell],
) -> bool:
    if start is None or end is None:
        return False

    (start_row, start_col), (end_row, end_col) = normalize_selection(start, end)

    if row < start_row or row > end_row:
        return False

    if row == start_row and row == end_row:
        return start_col <= col < end_col
    if row == start_row:
        return col >= start_col
    if row == end_row:
        return col < end_col
    return True


def selected_text(
    start: Optional[Cell],
    end: Optional[Cell],
    line_provider: Callable[[int], str],
) -> str:
    if start is None or end is None:
        return ""

    (start_row, start_col), (end_row, end_col) = normalize_selection(start, end)
    lines = []
    for row in range(start_row, end_row + 1):
        line_text = line_provider(row)
        if row == start_row and row == end_row:
            lines.append(line_text[start_col:end_col])
        elif row == start_row:
            lines.append(line_text[start_col:])
        elif row == end_row:
            lines.append(line_text[:end_col])
        else:
            lines.append(line_text)
    return "\n".join(lines)
