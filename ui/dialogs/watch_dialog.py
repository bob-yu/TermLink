from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QDialog, QHBoxLayout, QLabel, QLineEdit


class WatchDialog(QDialog):
    watch_changed = pyqtSignal(str)
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Watch")
        self.setFixedSize(330, 42)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._pending = False
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("""
            QDialog {
                background: #f8fafc;
                border: 1px solid #d8dee4;
                color: #24292f;
            }
            QLineEdit#watchEdit {
                background: #ffffff;
                border: 1px solid #d0d7de;
                border-radius: 4px;
                color: #24292f;
                font-size: 12px;
                padding: 2px 8px;
                selection-background-color: #dbeafe;
                selection-color: #24292f;
            }
            QLineEdit#watchEdit:focus { border-color: #0969da; }
            QLabel#countLabel {
                background: #ddf4ff;
                border: 1px solid #b6e3ff;
                border-radius: 4px;
                color: #0969da;
                font-size: 12px;
                font-weight: 600;
                min-width: 72px;
                padding: 2px 8px;
            }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 7, 8, 7)
        layout.setSpacing(6)

        self.watch_edit = QLineEdit()
        self.watch_edit.setObjectName("watchEdit")
        self.watch_edit.setPlaceholderText("Watch word")
        self.watch_edit.returnPressed.connect(self._emit_watch)
        self.watch_edit.textEdited.connect(self._mark_pending)
        self.watch_edit.setFixedHeight(24)
        layout.addWidget(self.watch_edit, 1)

        self.count_label = QLabel("0")
        self.count_label.setObjectName("countLabel")
        self.count_label.setAlignment(Qt.AlignCenter)
        self.count_label.setFixedHeight(24)
        layout.addWidget(self.count_label)

        self.watch_edit.setFocus()

    def set_watch_text(self, text: str):
        text = (text or "").strip()
        if not text:
            return
        self.watch_edit.setText(text)
        self.clear_selection()
        self._emit_watch()

    def clear_selection(self):
        self.watch_edit.deselect()
        self.watch_edit.setCursorPosition(len(self.watch_edit.text()))
        self.watch_edit.clearFocus()

    def update_count(self, count: int):
        if self._pending:
            return
        self.count_label.setText(str(count))

    def _emit_watch(self):
        self._pending = False
        self.watch_changed.emit(self.watch_edit.text().strip())

    def _mark_pending(self):
        self._pending = True
        self.count_label.setText("Enter")

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)
