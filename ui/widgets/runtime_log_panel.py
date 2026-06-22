import logging
from datetime import datetime

from PyQt5.QtCore import QObject, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QDockWidget,
    QMenu,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)


class _QtLogEmitter(QObject):
    record_received = pyqtSignal(str)


class _QtLogHandler(logging.Handler):
    def __init__(self, emitter: _QtLogEmitter):
        super().__init__()
        self._emitter = emitter

    def emit(self, record: logging.LogRecord):
        try:
            self._emitter.record_received.emit(self.format(record))
        except Exception:
            self.handleError(record)


class RuntimeLogPanel(QDockWidget):
    """Dockable runtime log viewer backed by Python logging."""

    def __init__(self, parent=None):
        super().__init__("Runtime Log", parent)
        self.setObjectName("runtimeLogDock")
        self.setAllowedAreas(
            Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea | Qt.RightDockWidgetArea
        )

        self._emitter = _QtLogEmitter(self)
        self._records = []
        self._paused = False
        self._min_level = logging.INFO
        self._handler = _QtLogHandler(self._emitter)
        self._handler.setLevel(logging.DEBUG)
        self._handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", "%H:%M:%S")
        )
        self._emitter.record_received.connect(self.append_line)

        root = logging.getLogger()
        root.addHandler(self._handler)
        if root.level > logging.INFO:
            root.setLevel(logging.INFO)

        panel = QWidget(self)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 6, 8, 6)

        self._text = QPlainTextEdit(panel)
        self._text.setReadOnly(True)
        self._text.setMaximumBlockCount(2000)
        self._text.setPlaceholderText("Runtime logs will appear here")
        self._text.setContextMenuPolicy(Qt.CustomContextMenu)
        self._text.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self._text, 1)

        self.setWidget(panel)
        self.append_line(f"{datetime.now():%H:%M:%S} INFO [ui] Runtime log panel enabled")

    def append_line(self, text: str):
        level = self._parse_level(text)
        self._records.append((level, text))
        if len(self._records) > 2000:
            self._records = self._records[-2000:]
        if not self._paused and level >= self._min_level:
            self._text.appendPlainText(text)

    def clear(self):
        self._records.clear()
        self._text.clear()

    def _set_paused(self, paused: bool):
        self._paused = paused
        if not paused:
            self._apply_filter()

    def _apply_filter(self):
        if self._paused:
            return
        self._text.clear()
        for level, text in self._records:
            if level >= self._min_level:
                self._text.appendPlainText(text)

    def _set_min_level(self, level: int):
        self._min_level = level
        self._apply_filter()

    def _show_context_menu(self, pos):
        menu = QMenu(self._text)

        level_menu = menu.addMenu("Level")
        for label, level in (
            ("DEBUG", logging.DEBUG),
            ("INFO", logging.INFO),
            ("WARNING", logging.WARNING),
            ("ERROR", logging.ERROR),
        ):
            action = level_menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(level == self._min_level)
            action.triggered.connect(lambda _checked=False, value=level: self._set_min_level(value))

        pause_action = menu.addAction("Pause")
        pause_action.setCheckable(True)
        pause_action.setChecked(self._paused)
        pause_action.toggled.connect(self._set_paused)

        menu.addSeparator()
        menu.addAction("Copy All", self._copy_all)
        menu.addAction("Clear", self.clear)
        menu.exec_(self._text.mapToGlobal(pos))

    @staticmethod
    def _parse_level(text: str) -> int:
        if " ERROR " in text:
            return logging.ERROR
        if " WARNING " in text:
            return logging.WARNING
        if " DEBUG " in text:
            return logging.DEBUG
        return logging.INFO

    def _copy_all(self):
        cursor = self._text.textCursor()
        self._text.selectAll()
        self._text.copy()
        self._text.setTextCursor(cursor)

    def closeEvent(self, event):
        super().closeEvent(event)

    def dispose(self):
        logging.getLogger().removeHandler(self._handler)
