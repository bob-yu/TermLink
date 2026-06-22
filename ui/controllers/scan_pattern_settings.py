from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)


class ScanPatternSettingsController:
    COMMON_PATTERNS = (
        "/dev/ttyUSB*",
        "/dev/ttyACM*",
        "/dev/ttyS*",
        "/dev/ttyAMA*",
    )

    def __init__(self, main_window):
        self._main_window = main_window

    def show(self):
        dialog = QDialog(self._main_window)
        dialog.setWindowTitle("Scan Patterns")
        dialog.setMinimumWidth(500)

        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Serial device glob patterns:"))

        pattern_list = QListWidget()
        pattern_list.addItems(self._main_window.app_config.scan_patterns)
        layout.addWidget(pattern_list)

        button_layout = QHBoxLayout()

        add_btn = QPushButton("Add")
        add_btn.clicked.connect(lambda: self._add_pattern(pattern_list))
        button_layout.addWidget(add_btn)

        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda: self._remove_pattern(pattern_list))
        button_layout.addWidget(remove_btn)

        layout.addLayout(button_layout)

        quick_layout = QHBoxLayout()
        for pattern in self.COMMON_PATTERNS:
            button = QPushButton(pattern)
            button.clicked.connect(lambda _, value=pattern: self._quick_add_pattern(pattern_list, value))
            quick_layout.addWidget(button)
        layout.addLayout(quick_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec_() != QDialog.Accepted:
            return

        patterns = [pattern_list.item(i).text() for i in range(pattern_list.count())]
        if not patterns:
            QMessageBox.warning(self._main_window, "Warning", "At least one scan pattern is required.")
            return

        self._main_window.app_config.scan_patterns = patterns
        self._main_window.config_manager.save()
        self._main_window.statusbar.showMessage("Scan patterns updated.")

    def _add_pattern(self, pattern_list):
        pattern, ok = QInputDialog.getText(
            self._main_window,
            "Add Scan Pattern",
            "Pattern:",
            text="/dev/ttyUSB*",
        )
        if ok and pattern.strip():
            pattern_list.addItem(pattern.strip())

    @staticmethod
    def _remove_pattern(pattern_list):
        current = pattern_list.currentRow()
        if current >= 0:
            pattern_list.takeItem(current)

    @staticmethod
    def _quick_add_pattern(pattern_list, pattern: str):
        existing = [pattern_list.item(i).text() for i in range(pattern_list.count())]
        if pattern not in existing:
            pattern_list.addItem(pattern)
