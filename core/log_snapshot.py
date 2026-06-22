from collections import deque


def read_last_lines(path: str, line_count: int, encoding: str = "utf-8") -> str:
    if not path or line_count <= 0:
        return ""

    try:
        with open(path, "r", encoding=encoding, errors="replace") as f:
            return "".join(deque(f, maxlen=line_count))
    except OSError:
        return ""
