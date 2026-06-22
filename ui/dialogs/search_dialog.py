from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton


class SearchDialog(QDialog):
    search_requested = pyqtSignal(str, bool, bool, bool)
    find_next_requested = pyqtSignal()
    find_previous_requested = pyqtSignal()
    clear_requested = pyqtSignal()
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Find")
        self.setFixedSize(430, 48)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._history = []
        self._case_sensitive = False
        self._regex = False
        self._last_search = None
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(_SEARCH_DIALOG_STYLE)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 7, 8, 7)
        layout.setSpacing(4)

        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("searchEdit")
        self.search_edit.setPlaceholderText("Find")
        self.search_edit.returnPressed.connect(self._on_find_next)
        self.search_edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.search_edit, 1)

        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        self.case_btn = self._make_toggle_button("Aa", "Match Case")
        self.case_btn.clicked.connect(self._toggle_case)
        layout.addWidget(self.case_btn)

        self.regex_btn = self._make_toggle_button(".*", "Use Regular Expression")
        self.regex_btn.clicked.connect(self._toggle_regex)
        layout.addWidget(self.regex_btn)

        self.prev_btn = self._make_icon_button("↑", "Previous Match (Shift+F3)")
        self.prev_btn.clicked.connect(self._on_find_previous)
        layout.addWidget(self.prev_btn)

        self.next_btn = self._make_icon_button("↓", "Next Match (F3)")
        self.next_btn.clicked.connect(self._on_find_next)
        layout.addWidget(self.next_btn)

        self.close_btn = self._make_icon_button("×", "Close")
        self.close_btn.clicked.connect(self.close)
        layout.addWidget(self.close_btn)

        self.search_edit.setFocus()

    def set_search_text(self, text: str):
        text = (text or "").strip()
        if not text:
            return
        self.search_edit.setText(text)
        self.search_edit.selectAll()
        self._emit_live_search()

    def _make_icon_button(self, text: str, tooltip: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("findIconButton")
        button.setToolTip(tooltip)
        button.setFixedSize(28, 28)
        button.setAutoDefault(False)
        button.setDefault(False)
        return button

    def _make_toggle_button(self, text: str, tooltip: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("findToggleButton")
        button.setToolTip(tooltip)
        button.setCheckable(True)
        button.setFixedSize(30, 28)
        button.setAutoDefault(False)
        button.setDefault(False)
        return button

    def _toggle_case(self):
        self._case_sensitive = self.case_btn.isChecked()
        self._emit_live_search()

    def _toggle_regex(self):
        self._regex = self.regex_btn.isChecked()
        self._emit_live_search()

    def _save_history(self, text: str):
        if not text:
            return
        if text in self._history:
            self._history.remove(text)
        self._history.insert(0, text)
        del self._history[20:]

    def _on_text_changed(self, _text: str):
        self._emit_live_search()

    def _emit_live_search(self):
        self._emit_search_if_needed(force=True)

    def _emit_search_if_needed(self, force: bool = False):
        text = self.search_edit.text()
        if text:
            query = (text, self._case_sensitive, self._regex)
            if not force and query == self._last_search:
                return False
            self._last_search = query
            self.search_requested.emit(text, self._case_sensitive, self._regex, False)
            return True
        else:
            self.status_label.setText("")
            self.status_label.setProperty("state", "")
            self._refresh_status_style()
            self._last_search = None
            self.clear_requested.emit()
            return False

    def _on_find_next(self):
        text = self.search_edit.text()
        if not text:
            return
        self._save_history(text)
        self._emit_search_if_needed()
        self.find_next_requested.emit()

    def _on_find_previous(self):
        text = self.search_edit.text()
        if not text:
            return
        self._save_history(text)
        self._emit_search_if_needed()
        self.find_previous_requested.emit()

    def update_status(self, current: int, total: int):
        if total == 0:
            self.status_label.setProperty("state", "error")
            self.status_label.setText("No results")
        else:
            self.status_label.setProperty("state", "ok")
            self.status_label.setText(f"{current}/{total}")
        self._refresh_status_style()

    def _refresh_status_style(self):
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_F3:
            if event.modifiers() & Qt.ShiftModifier:
                self._on_find_previous()
            else:
                self._on_find_next()
        else:
            super().keyPressEvent(event)


_SEARCH_DIALOG_STYLE = """
QDialog {
    background: #f8fafc;
    border: 1px solid #d8dee4;
    color: #24292f;
}
QLineEdit#searchEdit {
    background: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 4px;
    color: #24292f;
    font-size: 12px;
    padding: 4px 8px;
    selection-background-color: #0969da;
    selection-color: #ffffff;
}
QLineEdit#searchEdit:focus {
    border-color: #0969da;
}
QLabel#statusLabel {
    color: #57606a;
    font-size: 11px;
    min-width: 54px;
    background: transparent;
}
QLabel#statusLabel[state="ok"] {
    color: #57606a;
}
QLabel#statusLabel[state="error"] {
    color: #cf222e;
}
QPushButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
    color: #24292f;
    font-size: 12px;
    padding: 0;
}
QPushButton:hover {
    background: #eef2f7;
    border-color: #cbd5e1;
}
QPushButton:pressed {
    background: #e2e8f0;
}
QPushButton:checked {
    background: #0969da;
    border-color: #0969da;
    color: #ffffff;
}
QPushButton:default {
    background: transparent;
    border-color: transparent;
    color: #24292f;
}
QPushButton:default:hover {
    background: #eef2f7;
    border-color: #cbd5e1;
}
QPushButton#findToggleButton {
    font-weight: 600;
}
QPushButton#findToggleButton:checked {
    background: #0969da;
    border-color: #0969da;
    color: #ffffff;
}
QPushButton#findIconButton {
    font-size: 15px;
}
"""
