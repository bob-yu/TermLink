from collections import deque


class ScrollbackBuffer:
    def __init__(self, max_lines: int = 5000):
        self._max_lines = max_lines
        self._lines = deque(maxlen=max_lines)

    @property
    def max_lines(self) -> int:
        return self._max_lines

    @max_lines.setter
    def max_lines(self, value: int):
        self._max_lines = value
        self._lines = deque(self._lines, maxlen=value)

    def __len__(self) -> int:
        return len(self._lines)

    def append(self, line: str):
        self._lines.append(line)

    def get_line(self, index: int) -> str:
        if 0 <= index < len(self._lines):
            return self._lines[index]
        return ""

    def get_lines(self, start: int, count: int) -> list:
        result = []
        for index in range(start, min(start + count, len(self._lines))):
            if 0 <= index < len(self._lines):
                result.append(self._lines[index])
            else:
                result.append("")
        return result

    def clear(self):
        self._lines.clear()
