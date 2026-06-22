import re
from typing import Iterable, List, Tuple


SearchMatch = Tuple[int, int, int]


def find_matches(
    lines: Iterable[Tuple[int, str]],
    text: str,
    case_sensitive: bool = False,
    regex: bool = False,
) -> List[SearchMatch]:
    if not text:
        return []

    if regex:
        try:
            pattern = re.compile(text, 0 if case_sensitive else re.IGNORECASE)
        except re.error:
            return []
        return [
            (row, match.start(), match.end())
            for row, line in lines
            if line
            for match in pattern.finditer(line)
        ]

    needle = text if case_sensitive else text.lower()
    matches: List[SearchMatch] = []
    for row, line in lines:
        if not line:
            continue
        search_line = line if case_sensitive else line.lower()
        start = 0
        while True:
            pos = search_line.find(needle, start)
            if pos == -1:
                break
            matches.append((row, pos, pos + len(needle)))
            start = pos + 1
    return matches


def initial_match_index(
    matches: List[SearchMatch],
    current_abs_row: int,
    direction_up: bool,
) -> int:
    if not matches:
        return -1

    if not direction_up:
        return 0

    for index in range(len(matches) - 1, -1, -1):
        if matches[index][0] <= current_abs_row:
            return index
    return len(matches) - 1
