"""High-performance terminal widget with scrollback history."""
import pyte
from pyte.screens import Margins
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollBar, QApplication,
    QPushButton, QCheckBox,
)
from core.scrollback_buffer import ScrollbackBuffer
from .terminal_context_menu import build_terminal_context_menu
from .terminal_keymap import control_sequence, key_sequence
from .terminal_selection import (
    is_cell_selected,
    is_word_char,
    selected_text,
)
from .terminal_search import find_matches, initial_match_index
from .dialogs import SearchDialog, WatchDialog
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import (
    QPainter, QColor, QFont, QFontDatabase, QFontMetrics,
    QPalette, QKeyEvent, QImage
)
from .terminal_colors import BG_COLOR, FG_COLOR, terminal_color


class TrackingScreen(pyte.Screen):
    def __init__(self, columns: int, lines: int, scroll_callback=None):
        self._scroll_callback = scroll_callback
        super().__init__(columns, lines)

    def index(self) -> None:
        top, bottom = self.margins or Margins(0, self.lines - 1)
        if self.cursor.y == bottom and self._scroll_callback:
            self._scroll_callback(self.buffer[top])
        super().index()

    def erase_in_display(self, how: int = 0, *args, **kwargs) -> None:
        super().erase_in_display(how, *args, **kwargs)
        if how == 3 and self._scroll_callback:
            self._scroll_callback(None)


class TerminalView(QWidget):
    """Terminal viewport with scrollback, selection, search, highlight, and watch support."""
    scroll_changed = pyqtSignal(int, int)  # (current, maximum)
    watch_count_changed = pyqtSignal(int)
    terminal_resized = pyqtSignal(int, int)  # (columns, rows)

    def __init__(
        self,
        send_callback,
        scrollback_lines: int = 5000,
        parent=None,
        font_family: str = "",
        font_size: int = 11,
    ):
        super().__init__(parent)
        self._send_callback = send_callback

        self._font = self._make_font(font_family, font_size)
        self._update_font_metrics()
        # Terminal size in character cells.
        self.cols = 80
        self.rows = 24

        self._suppress_scrollback_capture = False
        self._screen = self._make_screen(self.cols, self.rows)
        self._screen.set_mode(pyte.modes.LNM)
        self._stream = pyte.Stream(self._screen)
        self._alternate_screen = None

        # Scrollback history.
        self._scrollback = ScrollbackBuffer(scrollback_lines)

        self._scroll_offset = 0
        self._auto_scroll = True

        self._buffer: QImage = None
        self._buffer_dirty = True

        # Deferred update timer keeps bursty terminal output responsive.
        self._pending_data = ""
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._do_deferred_update)
        self._update_interval = 16  # About 60 fps.
        self._layout_refresh_timer = QTimer()
        self._layout_refresh_timer.setSingleShot(True)
        self._layout_refresh_timer.timeout.connect(self._apply_pending_layout)
        self._pending_layout_size = None

        # Cursor.
        self._cursor_visible = True
        self._cursor_timer = QTimer()
        self._cursor_timer.timeout.connect(self._blink_cursor)
        self._cursor_timer.start(530)
        self._selection_scroll_timer = QTimer()
        self._selection_scroll_timer.timeout.connect(self._auto_scroll_selection)
        self._selection_scroll_margin = 24
        self._selection_scroll_step = 0
        self._last_mouse_pos = None

        # Selection state.
        self._selecting = False
        self._selection_start = None
        self._selection_end = None
        self._has_selection = False

        self._search_text = ""
        self._search_matches = []  # [(absolute_row, start_col, end_col), ...]
        self._current_match_index = -1
        self._search_case_sensitive = False
        self._search_regex = False
        self._highlight_matches = True
        self._highlight_rules = []
        self._highlight_rule_matches = []
        self._watch_text = ""
        self._watch_count = 0
        self._watch_matches = []

        self._log_enabled = True

        self._sysrq_mode = False
        self._sysrq_callback = None

        self.setFocusPolicy(Qt.StrongFocus)
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.Window, BG_COLOR)
        self.setPalette(palette)

        self.setMinimumSize(400, 200)

        self.setMouseTracking(True)

    def set_scrollback_lines(self, lines: int):
        """Terminal widget helper."""
        self._scrollback.max_lines = lines

    def _make_screen(self, cols: int, rows: int):
        return TrackingScreen(cols, rows, self._on_screen_scroll_line)

    def _on_screen_scroll_line(self, line):
        if self._suppress_scrollback_capture:
            return
        if line is None:
            self._scrollback.clear()
            return
        self._scrollback.append(self._line_to_text(line))

    def _line_to_text(self, line) -> str:
        text = ""
        for x in range(self.cols):
            char = line[x]
            text += char.data if hasattr(char, 'data') and char.data else ' '
        return text.rstrip()

    def set_terminal_font(self, family: str = "", point_size: int = 11):
        self._font = self._make_font(family, point_size)
        self._update_font_metrics()
        self._resize_terminal(
            max(40, (self.width() - 4) // self._char_width),
            max(10, (self.height() - 4) // self._char_height),
        )
        self._buffer_dirty = True
        self.update()

    def set_highlight_rules(self, rules):
        self._highlight_rules = [
            rule
            for rule in rules
            if getattr(rule, "enabled", False) and getattr(rule, "pattern", "")
        ]
        self._rebuild_highlight_matches()
        self._rebuild_watch_highlight_matches()
        self._buffer_dirty = True
        self.update()

    @staticmethod
    def _make_font(family: str = "", point_size: int = 11) -> QFont:
        font = QFont(family) if family else QFontDatabase.systemFont(QFontDatabase.FixedFont)
        font.setPointSize(point_size)
        font.setStyleHint(QFont.Monospace)
        font.setFixedPitch(True)
        return font

    def _update_font_metrics(self):
        fm = QFontMetrics(self._font)
        self._char_width = max(1, fm.horizontalAdvance("M"))
        self._char_height = max(1, fm.height())
        self._char_ascent = fm.ascent()

    def resizeEvent(self, event):
        """Terminal widget helper."""
        super().resizeEvent(event)
        self.refresh_layout(deferred=True)

    def refresh_layout(self, deferred: bool = True):
        """Refresh terminal geometry after tab split, merge, or reparent."""
        self._pending_layout_size = self.size()
        if deferred:
            self._layout_refresh_timer.start(25)
            return
        self._apply_pending_layout()

    def _apply_pending_layout(self):
        size = self._pending_layout_size or self.size()
        self._pending_layout_size = None

        new_width = size.width()
        new_height = size.height()

        if new_width <= 0 or new_height <= 0:
            return

        new_cols = max(40, (new_width - 4) // self._char_width)
        new_rows = max(10, (new_height - 4) // self._char_height)

        if new_cols != self.cols or new_rows != self.rows:
            self._resize_terminal(new_cols, new_rows)
            self.terminal_resized.emit(new_cols, new_rows)

        self._buffer = QImage(new_width, new_height, QImage.Format_RGB32)
        self._buffer_dirty = True
        self._rebuild_highlight_matches()
        self._rebuild_watch_highlight_matches()
        self.update()

    def _resize_terminal(self, new_cols: int, new_rows: int):
        """Terminal widget helper."""
        self.cols, self.rows = new_cols, new_rows

        # Keep pyte's screen model intact during split/merge/tab drag resizes.
        # Replaying visible text into a new screen can move the cursor and create
        # phantom blank lines because control state is lost.
        self._screen.resize(lines=new_rows, columns=new_cols)
        self._screen.cursor.x = min(getattr(self._screen.cursor, "x", 0), new_cols - 1)
        self._screen.cursor.y = min(getattr(self._screen.cursor, "y", 0), new_rows - 1)
        self._screen.set_margins()
        if self._auto_scroll:
            self._scroll_offset = 0
        self._buffer_dirty = True

    def _screen_snapshot_lines(self) -> list:
        return [self._get_screen_line_text(y) for y in range(self._screen.lines)]

    def _restore_screen_snapshot(self, lines: list, cursor_x: int, cursor_y: int):
        visible_lines = lines[-self.rows:]
        if not visible_lines:
            return
        text = "\r\n".join(line[:self.cols] for line in visible_lines)
        if text:
            self._stream.feed(text)
        self._screen.cursor.x = min(cursor_x, self.cols - 1)
        self._screen.cursor.y = min(cursor_y, self.rows - 1)

    def feed(self, data: str):
        """Terminal widget helper."""
        if not data:
            return

        data = self._handle_terminal_queries(data)
        data = self._handle_alternate_screen(data)
        if not data:
            return
        self._pending_data += data

        # Limit pending data to avoid unbounded memory growth.
        if len(self._pending_data) > 1024 * 1024:  # 1MB
            self._pending_data = self._pending_data[-512 * 1024:]

        # Start the deferred update timer if it is not already running.
        if not self._update_timer.isActive():
            self._update_timer.start(self._update_interval)

    def _handle_terminal_queries(self, data: str):
        if not self._send_callback:
            return data
        if "\x1b[c" in data or "\x1b[0c" in data:
            self._send_callback("\x1b[?1;2c")
        if "\x1b[>c" in data or "\x1b[>0c" in data:
            self._send_callback("\x1b[>0;276;0c")
        for sequence in ("\x1b[1t", "\x1b[c", "\x1b[0c", "\x1b[>c", "\x1b[>0c"):
            data = data.replace(sequence, "")
        return data

    def _handle_alternate_screen(self, data: str):
        enter_sequences = ("\x1b[?1049h", "\x1b[?1047h", "\x1b[?47h")
        leave_sequences = ("\x1b[?1049l", "\x1b[?1047l", "\x1b[?47l")

        for sequence in enter_sequences:
            if sequence in data:
                before, after = data.split(sequence, 1)
                if before:
                    self._stream.feed(before)
                self._enter_alternate_screen()
                return self._handle_alternate_screen(after)

        for sequence in leave_sequences:
            if sequence in data:
                before, after = data.split(sequence, 1)
                if before:
                    self._stream.feed(before)
                self._leave_alternate_screen()
                return self._handle_alternate_screen(after)

        return data

    def _enter_alternate_screen(self):
        if self._alternate_screen is None:
            self._alternate_screen = (
                self._screen_snapshot_lines(),
                getattr(self._screen.cursor, "x", 0),
                getattr(self._screen.cursor, "y", 0),
            )
        self._screen = self._make_screen(self.cols, self.rows)
        self._screen.set_mode(pyte.modes.LNM)
        self._stream = pyte.Stream(self._screen)
        self._buffer_dirty = True

    def _leave_alternate_screen(self):
        saved = self._alternate_screen
        self._alternate_screen = None
        self._screen = self._make_screen(self.cols, self.rows)
        self._screen.set_mode(pyte.modes.LNM)
        self._stream = pyte.Stream(self._screen)
        if saved:
            lines, cursor_x, cursor_y = saved
            self._suppress_scrollback_capture = True
            try:
                self._restore_screen_snapshot(lines, cursor_x, cursor_y)
            finally:
                self._suppress_scrollback_capture = False
        self._buffer_dirty = True

    def _do_deferred_update(self):
        """Terminal widget helper."""
        if not self._pending_data:
            return

        data = self._pending_data
        self._pending_data = ""

        try:
            self._stream.feed(data)

            self._buffer_dirty = True

            if self._auto_scroll:
                self._scroll_offset = 0

            self._rebuild_highlight_matches()
            self._count_watch_increment(data)
            self._rebuild_watch_highlight_matches()
            if self.isVisible():
                self.update()

            self._emit_scroll_info()
        except Exception as e:
            print(f"Terminal feed error: {e}")

    def _get_screen_line_text(self, y: int) -> str:
        """Terminal widget helper."""
        if y < 0 or y >= self._screen.lines:
            return ""
        line = self._screen.buffer[y]
        text = ""
        for x in range(self._screen.columns):
            char = line[x]
            text += char.data if hasattr(char, 'data') and char.data else ' '
        return text.rstrip()

    def clear(self):
        """Terminal widget helper."""
        self._screen.reset()
        self._alternate_screen = None
        self._scrollback.clear()
        self._scroll_offset = 0
        self._auto_scroll = True
        self._watch_matches = []
        self._rebuild_highlight_matches()
        self._rebuild_watch_highlight_matches()
        self._buffer_dirty = True
        self.update()
        self._emit_scroll_info()

    def scroll_lines(self, delta: int):
        """Terminal widget helper."""
        max_scroll = len(self._scrollback)

        new_offset = self._scroll_offset + delta
        new_offset = max(0, min(new_offset, max_scroll))

        if new_offset != self._scroll_offset:
            self._scroll_offset = new_offset
            self._auto_scroll = (new_offset == 0)
            self._rebuild_highlight_matches()
            self._rebuild_watch_highlight_matches()
            self._buffer_dirty = True
            self.update()
            self._emit_scroll_info()

    def scroll_to_bottom(self):
        """Terminal widget helper."""
        if self._scroll_offset != 0:
            self._scroll_offset = 0
            self._auto_scroll = True
            self._rebuild_highlight_matches()
            self._rebuild_watch_highlight_matches()
            self._buffer_dirty = True
            self.update()
            self._emit_scroll_info()

    def set_scroll_position(self, pos: int):
        """Terminal widget helper."""
        max_scroll = len(self._scrollback)
        new_offset = max_scroll - pos
        new_offset = max(0, min(new_offset, max_scroll))

        if new_offset != self._scroll_offset:
            self._scroll_offset = new_offset
            self._auto_scroll = (new_offset == 0)
            self._rebuild_highlight_matches()
            self._rebuild_watch_highlight_matches()
            self._buffer_dirty = True
            self.update()

    def _emit_scroll_info(self):
        """Terminal widget helper."""
        max_scroll = len(self._scrollback)
        current = max_scroll - self._scroll_offset
        self.scroll_changed.emit(current, max_scroll)

    def _blink_cursor(self):
        """Terminal widget helper."""
        self._cursor_visible = not self._cursor_visible
        if self._scroll_offset == 0:
            cx = self._screen.cursor.x
            cy = self._screen.cursor.y
            self.update(
                cx * self._char_width + 2,
                cy * self._char_height + 2,
                self._char_width,
                self._char_height
            )

    def paintEvent(self, event):
        """Terminal widget helper."""
        if self._buffer is None:
            self.refresh_layout(deferred=False)
        if self._buffer is None:
            return
        if self._buffer_dirty:
            self._render_buffer()

        painter = QPainter(self)
        painter.drawImage(0, 0, self._buffer)

        if self._cursor_visible and self.hasFocus() and self._scroll_offset == 0:
            cx = self._screen.cursor.x * self._char_width + 2
            cy = self._screen.cursor.y * self._char_height + 2
            painter.fillRect(cx, cy, self._char_width, self._char_height,
                           QColor(200, 200, 200, 180))

    def _render_buffer(self):
        """Terminal widget helper."""
        if not self._buffer:
            return

        painter = QPainter(self._buffer)
        painter.setFont(self._font)
        painter.fillRect(self._buffer.rect(), BG_COLOR)

        history_count = len(self._scrollback)

        if self._scroll_offset == 0:
            for y in range(min(self.rows, self._screen.lines)):
                self._render_screen_line(painter, y)
        else:
            for y in range(self.rows):
                source_line = history_count - self._scroll_offset + y

                if source_line < 0:
                    continue
                elif source_line < history_count:
                    text = self._scrollback.get_line(source_line)
                    self._render_text_line(painter, y, text)
                else:
                    screen_y = source_line - history_count
                    if screen_y < self._screen.lines:
                        self._render_screen_line(painter, y, screen_y)

        painter.end()
        self._buffer_dirty = False

    def _visible_lines(self):
        history_count = len(self._scrollback)
        lines = []
        if self._scroll_offset == 0:
            for y in range(min(self.rows, self._screen.lines)):
                lines.append((history_count + y, self._get_screen_line_text(y)))
        else:
            for y in range(self.rows):
                source_line = history_count - self._scroll_offset + y
                if source_line < 0:
                    continue
                if source_line < history_count:
                    lines.append((source_line, self._scrollback.get_line(source_line)))
                else:
                    screen_y = source_line - history_count
                    if screen_y < self._screen.lines:
                        lines.append((source_line, self._get_screen_line_text(screen_y)))
        return lines

    def _rebuild_highlight_matches(self):
        self._highlight_rule_matches = []
        if not self._highlight_rules:
            return
        lines = self._visible_lines()
        for rule_index, rule in enumerate(self._highlight_rules):
            matches = find_matches(
                lines,
                rule.pattern,
                getattr(rule, "case_sensitive", False),
                getattr(rule, "regex", False),
            )
            for abs_row, start_col, end_col in matches:
                self._highlight_rule_matches.append((abs_row, start_col, end_col, rule_index))

    def _render_screen_line(self, painter: QPainter, display_y: int, screen_y: int = None):
        """Terminal widget helper."""
        if screen_y is None:
            screen_y = display_y

        if screen_y >= self._screen.lines:
            return

        line = self._screen.buffer[screen_y]
        py = display_y * self._char_height + 2

        for x in range(min(len(line), self.cols)):
            char = line[x]
            px = x * self._char_width + 2

            is_selected = self._is_cell_selected(display_y, x)

            is_match, is_current_match = self._is_cell_search_match(display_y, x)
            highlight_color = self._cell_highlight_color(display_y, x)

            # Cell background.
            bg = char.bg if hasattr(char, 'bg') else "default"
            if is_selected:
                painter.fillRect(
                    px, py, self._char_width, self._char_height,
                    QColor(51, 153, 255, 180),
                )
            elif is_current_match:
                painter.fillRect(px, py, self._char_width, self._char_height,
                               QColor(255, 150, 50, 200))
            elif is_match:
                painter.fillRect(px, py, self._char_width, self._char_height,
                               QColor(255, 255, 0, 150))
            elif highlight_color is not None:
                painter.fillRect(px, py, self._char_width, self._char_height, highlight_color)
            elif bg != "default":
                painter.fillRect(
                    px,
                    py,
                    self._char_width,
                    self._char_height,
                    terminal_color(bg, BG_COLOR),
                )

            fg = char.fg if hasattr(char, 'fg') else "default"
            color = terminal_color(fg, FG_COLOR)

            if hasattr(char, 'reverse') and char.reverse and not is_selected and not is_match:
                painter.fillRect(px, py, self._char_width, self._char_height, color)
                color = BG_COLOR

            if is_selected:
                color = QColor(255, 255, 255)
            elif is_match or highlight_color is not None:
                color = QColor(0, 0, 0)

            char_data = char.data if hasattr(char, 'data') else ' '
            if char_data and char_data != ' ':
                base_font = painter.font()
                styled_font = None
                if getattr(char, "bold", False) or getattr(char, "italics", False):
                    styled_font = QFont(base_font)
                    styled_font.setBold(bool(getattr(char, "bold", False)))
                    styled_font.setItalic(bool(getattr(char, "italics", False)))
                    painter.setFont(styled_font)
                painter.setPen(color)
                painter.drawText(px, py + self._char_ascent, char_data)
                if getattr(char, "underscore", False):
                    underline_y = py + self._char_ascent + 1
                    painter.drawLine(px, underline_y, px + self._char_width, underline_y)
                if getattr(char, "strikethrough", False):
                    strike_y = py + self._char_height // 2
                    painter.drawLine(px, strike_y, px + self._char_width, strike_y)
                if styled_font is not None:
                    painter.setFont(base_font)

    def _render_text_line(self, painter: QPainter, display_y: int, text: str):
        """Terminal widget helper."""
        py = display_y * self._char_height + 2

        for x, char in enumerate(text[:self.cols]):
            px = x * self._char_width + 2

            is_selected = self._is_cell_selected(display_y, x)

            is_match, is_current_match = self._is_cell_search_match(display_y, x)
            highlight_color = self._cell_highlight_color(display_y, x)

            if is_selected:
                painter.fillRect(px, py, self._char_width, self._char_height,
                               QColor(51, 153, 255, 180))
                painter.setPen(QColor(255, 255, 255))
            elif is_current_match:
                painter.fillRect(px, py, self._char_width, self._char_height,
                               QColor(255, 150, 50, 200))
                painter.setPen(QColor(0, 0, 0))
            elif is_match:
                painter.fillRect(px, py, self._char_width, self._char_height,
                               QColor(255, 255, 0, 150))
                painter.setPen(QColor(0, 0, 0))
            elif highlight_color is not None:
                painter.fillRect(px, py, self._char_width, self._char_height, highlight_color)
                painter.setPen(QColor(0, 0, 0))
            else:
                painter.setPen(FG_COLOR)

            if char and char != ' ':
                painter.drawText(px, py + self._char_ascent, char)

    def wheelEvent(self, event):
        """Terminal widget helper."""
        delta = event.angleDelta().y()
        lines = 3 if delta > 0 else -3
        self.scroll_lines(lines)
        event.accept()

    def mousePressEvent(self, event):
        """Terminal widget helper."""
        self.setFocus()
        if event.button() == Qt.LeftButton:
            self._clear_selection()
            self._selecting = True
            pos = self._pixel_to_cell(event.pos())
            self._selection_start = pos
            self._selection_end = pos
        elif event.button() == Qt.RightButton:
            self._show_context_menu(event.globalPos())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Terminal widget helper."""
        if self._selecting and event.buttons() & Qt.LeftButton:
            self._last_mouse_pos = event.pos()
            self._update_selection_auto_scroll(event.pos())
            pos = self._pixel_to_cell(event.pos())
            if pos != self._selection_end:
                self._selection_end = pos
                self._has_selection = True
                self._buffer_dirty = True
                self.update()

    def mouseReleaseEvent(self, event):
        """Terminal widget helper."""
        if event.button() == Qt.LeftButton and self._selecting:
            self._selecting = False
            self._stop_selection_auto_scroll()
            if self._has_selection:
                selected_text = self._get_selected_text()
                if selected_text:
                    clipboard = QApplication.clipboard()
                    clipboard.setText(selected_text)
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Terminal widget helper."""
        if event.button() == Qt.LeftButton:
            pos = self._pixel_to_cell(event.pos())
            row, col = pos
            line_text = self._get_display_line_text(row)

            if col < len(line_text):
                # Find word boundaries.
                start = col
                end = col

                while start > 0 and self._is_word_char(line_text[start - 1]):
                    start -= 1

                while end < len(line_text) and self._is_word_char(line_text[end]):
                    end += 1

                if end > start:
                    self._selection_start = (row, start)
                    self._selection_end = (row, end)
                    self._has_selection = True
                    self._buffer_dirty = True
                    self.update()

                    word = line_text[start:end]
                    if word:
                        clipboard = QApplication.clipboard()
                        clipboard.setText(word)

    def _is_word_char(self, char: str) -> bool:
        """Terminal widget helper."""
        return is_word_char(char)

    def _pixel_to_cell(self, pos) -> tuple:
        """Terminal widget helper."""
        col = max(0, min((pos.x() - 2) // self._char_width, self.cols - 1))
        row = max(0, min((pos.y() - 2) // self._char_height, self.rows - 1))
        return (row, col)

    def _clear_selection(self):
        """Terminal widget helper."""
        self._stop_selection_auto_scroll()
        if self._has_selection:
            self._has_selection = False
            self._selection_start = None
            self._selection_end = None
            self._buffer_dirty = True
            self.update()

    def _update_selection_auto_scroll(self, pos):
        if pos.y() < self._selection_scroll_margin:
            self._selection_scroll_step = 1
        elif pos.y() > self.height() - self._selection_scroll_margin:
            self._selection_scroll_step = -1
        else:
            self._stop_selection_auto_scroll()
            return
        if not self._selection_scroll_timer.isActive():
            self._selection_scroll_timer.start(50)

    def _stop_selection_auto_scroll(self):
        self._selection_scroll_step = 0
        self._last_mouse_pos = None
        if self._selection_scroll_timer.isActive():
            self._selection_scroll_timer.stop()

    def _auto_scroll_selection(self):
        if not self._selecting or self._selection_scroll_step == 0:
            self._stop_selection_auto_scroll()
            return
        previous_offset = self._scroll_offset
        self.scroll_lines(self._selection_scroll_step)
        if self._scroll_offset == previous_offset:
            self._stop_selection_auto_scroll()
            return
        if self._last_mouse_pos is not None:
            self._selection_end = self._pixel_to_cell(self._last_mouse_pos)
            self._has_selection = True
            self._buffer_dirty = True
            self.update()

    def _get_display_line_text(self, display_row: int) -> str:
        """Terminal widget helper."""
        history_count = len(self._scrollback)
        source_line = history_count - self._scroll_offset + display_row

        if source_line < 0:
            return ""
        elif source_line < history_count:
            return self._scrollback.get_line(source_line)
        else:
            screen_y = source_line - history_count
            if screen_y < self._screen.lines:
                return self._get_screen_line_text(screen_y)
        return ""

    def _get_selected_text(self) -> str:
        """Terminal widget helper."""
        if not self._has_selection:
            return ""
        return selected_text(
            self._selection_start,
            self._selection_end,
            self._get_display_line_text,
        )

    def _is_cell_selected(self, row: int, col: int) -> bool:
        """Terminal widget helper."""
        if not self._has_selection:
            return False
        return is_cell_selected(row, col, self._selection_start, self._selection_end)

    # ========== Search ==========

    def search(self, text: str, case_sensitive: bool = False, regex: bool = False,
               direction_up: bool = True) -> int:
        """Search terminal text and return the match count."""
        self._search_text = text
        self._search_case_sensitive = case_sensitive
        self._search_regex = regex
        self._search_matches = []
        self._current_match_index = -1

        if not text:
            self._buffer_dirty = True
            self.update()
            return 0
        history_count = len(self._scrollback)
        total_lines = history_count + self._screen.lines

        lines = []
        for abs_row in range(total_lines):
            if abs_row < history_count:
                line = self._scrollback.get_line(abs_row)
            else:
                screen_row = abs_row - history_count
                line = self._get_screen_line_text(screen_row)
            lines.append((abs_row, line))

        self._search_matches = find_matches(lines, text, case_sensitive, regex)

        if self._search_matches:
            current_abs_row = history_count - self._scroll_offset
            self._current_match_index = initial_match_index(
                self._search_matches,
                current_abs_row,
                direction_up,
            )
            self._scroll_to_match(self._current_match_index)

        self._buffer_dirty = True
        self.update()
        return len(self._search_matches)

    def set_watch_text(self, text: str) -> int:
        self._watch_text = (text or "").strip()
        self._watch_count = 0
        self._rebuild_watch_highlight_matches()
        self.watch_count_changed.emit(0)
        self._buffer_dirty = True
        self.update()
        return self._watch_count

    def clear_watch(self):
        self._watch_text = ""
        self._watch_count = 0
        self._watch_matches = []
        self._buffer_dirty = True
        self.update()

    def watch_count(self) -> int:
        return self._watch_count

    def _all_terminal_lines(self):
        history_count = len(self._scrollback)
        lines = [(row, self._scrollback.get_line(row)) for row in range(history_count)]
        cursor_row = getattr(self._screen.cursor, "y", -1)
        for row in range(self._screen.lines):
            if row == cursor_row:
                continue
            lines.append((history_count + row, self._get_screen_line_text(row)))
        return lines

    def _count_watch_increment(self, data: str) -> int:
        if not self._watch_text:
            return 0
        increment = len(
            find_matches(
                [(0, data)],
                self._watch_text,
                case_sensitive=False,
                regex=False,
            )
        )
        if increment:
            self._watch_count += increment
            self.watch_count_changed.emit(self._watch_count)
        return increment

    def _rebuild_watch_highlight_matches(self):
        if not self._watch_text:
            self._watch_matches = []
            return
        self._watch_matches = find_matches(
            self._all_terminal_lines(),
            self._watch_text,
            case_sensitive=False,
            regex=False,
        )

    def find_next(self) -> bool:
        """Terminal widget helper."""
        if not self._search_matches:
            return False

        self._current_match_index = (self._current_match_index + 1) % len(self._search_matches)
        self._scroll_to_match(self._current_match_index)
        self._buffer_dirty = True
        self.update()
        return True

    def find_previous(self) -> bool:
        """Terminal widget helper."""
        if not self._search_matches:
            return False

        self._current_match_index = (self._current_match_index - 1) % len(self._search_matches)
        self._scroll_to_match(self._current_match_index)
        self._buffer_dirty = True
        self.update()
        return True

    def clear_search(self):
        """Terminal widget helper."""
        self._search_text = ""
        self._search_matches = []
        self._current_match_index = -1
        self._buffer_dirty = True
        self.update()

    def _scroll_to_match(self, match_index: int):
        """Terminal widget helper."""
        if match_index < 0 or match_index >= len(self._search_matches):
            return

        abs_row, start_col, end_col = self._search_matches[match_index]
        history_count = len(self._scrollback)

        # Center the active match in the visible terminal area when possible.
        target_display_row = self.rows // 2

        # abs_row = history_count - scroll_offset + display_row
        # scroll_offset = history_count - abs_row + display_row
        new_offset = history_count - abs_row + target_display_row
        new_offset = max(0, min(new_offset, history_count))

        if new_offset != self._scroll_offset:
            self._scroll_offset = new_offset
            self._auto_scroll = (new_offset == 0)
            self._rebuild_highlight_matches()
            self._rebuild_watch_highlight_matches()
            self._emit_scroll_info()

    def _is_cell_search_match(self, display_row: int, col: int) -> tuple:
        """Return whether the cell is a search match and the active match."""
        if not self._search_matches or not self._highlight_matches:
            return (False, False)

        history_count = len(self._scrollback)
        abs_row = history_count - self._scroll_offset + display_row

        for i, (match_row, start_col, end_col) in enumerate(self._search_matches):
            if match_row == abs_row and start_col <= col < end_col:
                is_current = (i == self._current_match_index)
                return (True, is_current)

        return (False, False)

    def _cell_highlight_color(self, display_row: int, col: int):
        watch_color = self._cell_watch_highlight_color(display_row, col)
        if watch_color is not None:
            return watch_color
        if not self._highlight_rule_matches:
            return None
        history_count = len(self._scrollback)
        abs_row = history_count - self._scroll_offset + display_row
        for match_row, start_col, end_col, rule_index in self._highlight_rule_matches:
            if match_row == abs_row and start_col <= col < end_col:
                if 0 <= rule_index < len(self._highlight_rules):
                    return QColor(getattr(self._highlight_rules[rule_index], "color", "#fff3cd"))
        return None

    def _cell_watch_highlight_color(self, display_row: int, col: int):
        if not self._watch_matches:
            return None
        history_count = len(self._scrollback)
        abs_row = history_count - self._scroll_offset + display_row
        for match_row, start_col, end_col in self._watch_matches:
            if match_row == abs_row and start_col <= col < end_col:
                return QColor("#ffec80")
        return None

    def get_match_info(self) -> tuple:
        """Terminal widget helper."""
        if not self._search_matches:
            return (0, 0)
        return (self._current_match_index + 1, len(self._search_matches))

    def keyPressEvent(self, event: QKeyEvent):
        """Terminal widget helper."""
        key = event.key()
        modifiers = event.modifiers()
        text = event.text()

        if key in (Qt.Key_Return, Qt.Key_Enter) and not self._is_session_connected():
            self._connect_session()
            return

        if self._sysrq_mode:
            self._sysrq_mode = False
            if text and text.isalpha():
                if self._send_callback:
                    self._send_callback(text.lower())
                return
            if key == Qt.Key_Escape:
                return
        # Ctrl+End: scroll to bottom.
        if modifiers & Qt.ControlModifier and key == Qt.Key_End:
            self.scroll_to_bottom()
            return

        # Shift+PageUp/Down: page through scrollback.
        if modifiers & Qt.ShiftModifier:
            if key == Qt.Key_PageUp:
                self.scroll_lines(self.rows)
                return
            elif key == Qt.Key_PageDown:
                self.scroll_lines(-self.rows)
                return

        data = None

        if modifiers & Qt.ControlModifier:
            if key == Qt.Key_V:
                clipboard = QApplication.clipboard()
                paste_text = clipboard.text()
                if paste_text and self._send_callback:
                    self._send_callback(paste_text)
                return
            data = control_sequence(key, Qt)
        else:
            data = key_sequence(key, text, Qt)

        if data and self._send_callback:
            if self._scroll_offset != 0:
                self.scroll_to_bottom()
            self._send_callback(data)

    def focusNextPrevChild(self, next):
        return False

    def showEvent(self, event):
        """Terminal widget helper."""
        super().showEvent(event)
        if self._buffer_dirty:
            self.update()

    def set_update_interval(self, ms: int):
        """Terminal widget helper."""
        self._update_interval = max(8, ms)

    def _show_context_menu(self, pos):
        """Terminal widget helper."""
        menu = build_terminal_context_menu(self)
        menu.exec_(pos)

    def _copy_selection(self):
        """Terminal widget helper."""
        if self._has_selection:
            selected_text = self._get_selected_text()
            if selected_text:
                clipboard = QApplication.clipboard()
                clipboard.setText(selected_text)

    def _paste_clipboard(self):
        """Terminal widget helper."""
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text and self._send_callback:
            self._send_callback(text)

    def _select_all(self):
        """Terminal widget helper."""
        total_lines = len(self._scrollback) + self.rows
        self._selection_start = (0, 0)
        self._selection_end = (total_lines - 1, self.cols - 1)
        self._has_selection = True
        self._buffer_dirty = True
        self.update()

    def _show_search_dialog(self):
        """Terminal widget helper."""
        selected_text = self._get_selected_text()
        parent = self._find_parent_with("show_search_dialog")
        if parent:
            parent.show_search_dialog(selected_text)
            if selected_text:
                self._clear_selection()

    def _show_watch_dialog(self):
        selected_text = self._get_selected_text()
        parent = self._find_parent_with("show_watch_dialog")
        if parent:
            parent.show_watch_dialog(selected_text)
            if selected_text:
                self._clear_selection()

    def _highlight_selection(self):
        selected_text = self._get_selected_text()
        parent = self._find_parent_with("_highlight_selection")
        if parent:
            parent._highlight_selection(selected_text)
            if selected_text:
                self._clear_selection()

    def _show_highlight_rules(self):
        selected_text = self._get_selected_text()
        parent = self._find_parent_with("_show_highlight_rules")
        if parent:
            parent._show_highlight_rules(selected_text)

    def _clear_highlight_rules(self):
        parent = self._find_parent_with("_clear_highlight_rules")
        if parent:
            parent._clear_highlight_rules()

    def _connect_session(self):
        parent = self._find_parent_with("_connect_session")
        if parent:
            parent._connect_session()

    def _disconnect_session(self):
        parent = self._find_parent_with("_disconnect_session")
        if parent:
            parent._disconnect_session()

    def _is_session_connected(self) -> bool:
        parent = self._find_parent_with("_is_session_connected")
        if parent:
            return parent._is_session_connected()
        return True

    def _send_break(self):
        """Terminal widget helper."""
        # Ask the parent session to send a serial Break signal.
        parent = self._find_parent_with("_send_serial_break")
        if parent:
            parent._send_serial_break()
            self._sysrq_mode = True
            self._show_sysrq_hint()
            return

        # Fall back to Ctrl+C when the parent session cannot send Break.
        if self._send_callback:
            self._send_callback('\x03')

    def _show_sysrq_hint(self):
        """Terminal widget helper."""
        # Keep this quiet to avoid injecting helper text into the terminal stream.
        pass

    def _exit_sysrq_mode(self):
        """Terminal widget helper."""
        self._sysrq_mode = False

    def _clear_current_screen(self):
        """Terminal widget helper."""
        self._screen.reset()
        self._buffer_dirty = True
        self.update()

    def _clear_scrollback(self):
        """Terminal widget helper."""
        self._scrollback.clear()
        self._scroll_offset = 0
        self._buffer_dirty = True
        self.update()
        self.scroll_changed.emit(0, 0)

    def _toggle_log(self, enabled: bool):
        """Terminal widget helper."""
        self._log_enabled = enabled
        parent = self._find_parent_with("_toggle_log")
        if parent:
            parent._toggle_log(enabled)

    def _open_log_file(self):
        """Terminal widget helper."""
        parent = self._find_parent_with("_open_log_file")
        if parent:
            parent._open_log_file()

    def _open_log_folder(self):
        """Terminal widget helper."""
        parent = self._find_parent_with("_open_log_folder")
        if parent:
            parent._open_log_folder()

    def _show_terminal_settings(self):
        parent = self._find_parent_with("_terminal_settings")
        if parent:
            parent._terminal_settings.show()
            return
        parent = self._find_parent_with("_show_terminal_settings")
        if parent:
            parent._show_terminal_settings()

    def _find_parent_with(self, attr_name: str):
        parent = self.parent()
        while parent:
            if hasattr(parent, attr_name):
                return parent
            parent = parent.parent()
        return None

    def cleanup(self):
        """Terminal widget helper."""
        self._update_timer.stop()
        self._cursor_timer.stop()

    def __del__(self):
        """Terminal widget helper."""
        try:
            self._update_timer.stop()
            self._cursor_timer.stop()
        except:
            pass


class TerminalWidget(QWidget):
    """Terminal widget with scrollbar and search."""

    terminal_resized = pyqtSignal(int, int)

    def __init__(
        self,
        send_callback,
        scrollback_lines: int = 5000,
        parent=None,
        font_family: str = "",
        font_size: int = 11,
    ):
        super().__init__(parent)
        self._send_callback = send_callback

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Terminal viewport.
        self._view = TerminalView(
            send_callback,
            scrollback_lines,
            font_family=font_family,
            font_size=font_size,
        )
        layout.addWidget(self._view, 1)

        self._scrollbar = QScrollBar(Qt.Vertical)
        self._scrollbar.setStyleSheet("""
            QScrollBar:vertical {
                background: #2d2d2d;
                width: 14px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #5a5a5a;
                min-height: 30px;
                border-radius: 5px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background: #787878;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)
        layout.addWidget(self._scrollbar)

        # Signal connections.
        self._view.scroll_changed.connect(self._on_view_scroll)
        self._view.watch_count_changed.connect(self._on_watch_count_changed)
        self._view.terminal_resized.connect(self.terminal_resized)
        self._scrollbar.valueChanged.connect(self._on_scrollbar_changed)

        self.setStyleSheet("background-color: #1e1e1e;")

        self._search_dialog = None
        self._watch_dialog = None
        self._watch_dialog_active = False
        self._watch_dialog_pos = None

    def _on_view_scroll(self, current: int, maximum: int):
        """Terminal widget helper."""
        self._scrollbar.blockSignals(True)
        self._scrollbar.setRange(0, maximum)
        self._scrollbar.setValue(current)
        self._scrollbar.setPageStep(self._view.rows)
        self._scrollbar.blockSignals(False)

    def _on_scrollbar_changed(self, value: int):
        """Terminal widget helper."""
        self._view.set_scroll_position(value)

    def set_scrollback_lines(self, lines: int):
        """Terminal widget helper."""
        self._view.set_scrollback_lines(lines)

    def set_terminal_font(self, family: str = "", point_size: int = 11):
        self._view.set_terminal_font(family, point_size)

    def set_highlight_rules(self, rules):
        self._view.set_highlight_rules(rules)

    def feed(self, data: str):
        self._view.feed(data)

    def clear(self):
        self._view.clear()

    def scroll_to_bottom_force(self):
        self._view.scroll_to_bottom()

    def refresh_layout(self):
        self._view.refresh_layout()

    def set_scroll_area(self, scroll_area):
        pass

    def setFocus(self):
        self._view.setFocus()

    # ========== Search ==========

    def show_search_dialog(self, initial_text: str = ""):
        """Terminal widget helper."""
        if self._search_dialog is None:
            self._search_dialog = SearchDialog(self)
            self._search_dialog.search_requested.connect(self._on_search)
            self._search_dialog.find_next_requested.connect(self._on_find_next)
            self._search_dialog.find_previous_requested.connect(self._on_find_previous)
            self._search_dialog.clear_requested.connect(self._view.clear_search)
            self._search_dialog.closed.connect(self._on_search_closed)

        if initial_text:
            self._search_dialog.set_search_text(initial_text)
        self._search_dialog.show()
        self._search_dialog.raise_()
        self._search_dialog.activateWindow()

    def show_watch_dialog(self, initial_text: str = ""):
        if self._watch_dialog is None:
            self._watch_dialog = WatchDialog(self)
            self._watch_dialog.watch_changed.connect(self._on_watch_changed)
            self._watch_dialog.closed.connect(self._on_watch_closed)
        self._watch_dialog_active = True

        if initial_text:
            self._watch_dialog.set_watch_text(initial_text)
        else:
            self._update_watch_dialog_count()
        self._watch_dialog.show()
        if self._watch_dialog_pos is not None:
            self._watch_dialog.move(self._watch_dialog_pos)
        self._watch_dialog.watch_edit.setFocus()
        self._watch_dialog.raise_()
        self._watch_dialog.activateWindow()

    def hide_watch_dialog(self):
        if self._watch_dialog:
            self._watch_dialog_pos = self._watch_dialog.pos()
            self._watch_dialog.clear_selection()
            self._watch_dialog.hide()

    def show_watch_if_active(self):
        if self._watch_dialog_active and self._watch_dialog:
            self._update_watch_dialog_count()
            self._watch_dialog.clear_selection()
            self._watch_dialog.show()
            if self._watch_dialog_pos is not None:
                self._watch_dialog.move(self._watch_dialog_pos)

    def close_watch_dialog(self):
        self._watch_dialog_active = False
        self._watch_dialog_pos = None
        self._view.clear_watch()
        if self._watch_dialog:
            dialog = self._watch_dialog
            self._watch_dialog = None
            dialog.deleteLater()

    def _on_watch_changed(self, text: str):
        count = self._view.set_watch_text(text)
        if self._watch_dialog:
            self._watch_dialog.update_count(count)

    def _update_watch_dialog_count(self):
        if self._watch_dialog:
            self._watch_dialog.update_count(self._view.watch_count())

    def _on_watch_count_changed(self, count: int):
        if self._watch_dialog:
            self._watch_dialog.update_count(count)

    def _on_watch_closed(self):
        self._watch_dialog_active = False
        if self._watch_dialog:
            self._watch_dialog_pos = self._watch_dialog.pos()
        self._view.clear_watch()
        if self._watch_dialog:
            self._watch_dialog.deleteLater()
            self._watch_dialog = None

    def _show_highlight_rules(self, selected_text: str = ""):
        parent = self._find_parent_with("_show_highlight_rules")
        if parent:
            parent._show_highlight_rules(selected_text)

    def _highlight_selection(self, selected_text: str = ""):
        parent = self._find_parent_with("_highlight_selection")
        if parent:
            parent._highlight_selection(selected_text)

    def _clear_highlight_rules(self):
        parent = self._find_parent_with("_clear_highlight_rules")
        if parent:
            parent._clear_highlight_rules()

    def _find_parent_with(self, attr_name: str):
        parent = self.parent()
        while parent:
            if hasattr(parent, attr_name):
                return parent
            parent = parent.parent()
        return None

    def _on_search(self, text: str, case_sensitive: bool, regex: bool, direction_up: bool):
        """Terminal widget helper."""
        count = self._view.search(text, case_sensitive, regex, direction_up)
        if self._search_dialog:
            current, total = self._view.get_match_info()
            self._search_dialog.update_status(current, total)

    def _on_find_next(self):
        """Terminal widget helper."""
        self._view.find_next()
        if self._search_dialog:
            current, total = self._view.get_match_info()
            self._search_dialog.update_status(current, total)

    def _on_find_previous(self):
        """Terminal widget helper."""
        self._view.find_previous()
        if self._search_dialog:
            current, total = self._view.get_match_info()
            self._search_dialog.update_status(current, total)

    def _on_search_closed(self):
        """Terminal widget helper."""
        self._view.clear_search()
        if self._search_dialog:
            self._search_dialog.deleteLater()
            self._search_dialog = None
