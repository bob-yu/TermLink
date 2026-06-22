from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from utils.config_schema import HighlightRuleData


DEFAULT_HIGHLIGHT_RULES = [
    HighlightRuleData("Errors", r"error|fail|failed|exception", "#ff8a8a", False, True, True),
    HighlightRuleData("Warnings", r"warning|warn", "#ffec80", False, True, True),
    HighlightRuleData("Success", r"success|ready|done|ok", "#a8f0a5", False, True, True),
    HighlightRuleData("Timeout", r"timeout|retry|disconnect", "#ffc078", False, True, True),
    HighlightRuleData("IP Address", r"\b\d{1,3}(?:\.\d{1,3}){3}\b", "#8cecff", False, True, True),
]


class HighlightRulesDialog(QDialog):
    def __init__(self, rules, selected_text: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Highlights")
        self.resize(720, 360)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._selected_text = (selected_text or "").strip()
        self._setup_ui()
        self._load_rules(rules)
        if self._selected_text and self.table.rowCount() == 0:
            self._add_rule_from_text(self._selected_text)

    def _setup_ui(self):
        self.setStyleSheet("""
            QDialog { background: #f8fafc; color: #24292f; }
            QTableWidget {
                background: #ffffff;
                border: 1px solid #d8dee4;
                gridline-color: #e5e7eb;
                selection-background-color: #ddf4ff;
                selection-color: #24292f;
            }
            QHeaderView::section {
                background: #f1f5f9;
                border: none;
                border-right: 1px solid #d8dee4;
                border-bottom: 1px solid #d8dee4;
                padding: 5px 6px;
                color: #24292f;
                font-weight: 600;
            }
            QPushButton {
                background: #ffffff;
                border: 1px solid #d0d7de;
                border-radius: 4px;
                color: #24292f;
                padding: 5px 12px;
            }
            QPushButton:hover { background: #eef2f7; border-color: #cbd5e1; }
            QPushButton:pressed { background: #e2e8f0; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.table = QTableWidget(0, 6, self)
        self.table.setHorizontalHeaderLabels(["Enabled", "Name", "Pattern", "Color", "Aa", ".*"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        layout.addWidget(self.table, 1)

        actions = QHBoxLayout()
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._add_empty_rule)
        actions.addWidget(add_btn)

        add_selected_btn = QPushButton("Add Selected Text")
        add_selected_btn.setEnabled(bool(self._selected_text))
        add_selected_btn.clicked.connect(lambda: self._add_rule_from_text(self._selected_text))
        actions.addWidget(add_selected_btn)

        color_btn = QPushButton("Color...")
        color_btn.clicked.connect(self._choose_color)
        actions.addWidget(color_btn)

        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(self._remove_selected_rule)
        actions.addWidget(remove_btn)

        defaults_btn = QPushButton("Add Defaults")
        defaults_btn.clicked.connect(self._add_default_rules)
        actions.addWidget(defaults_btn)
        actions.addStretch()
        layout.addLayout(actions)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_rules(self, rules):
        self.table.setRowCount(0)
        for rule in rules or []:
            self._append_rule(rule)

    def _add_default_rules(self):
        existing = {
            (
                self.table.item(row, 2).text().strip(),
                self.table.cellWidget(row, 4).isChecked(),
                self.table.cellWidget(row, 5).isChecked(),
            )
            for row in range(self.table.rowCount())
            if self.table.item(row, 2) and self.table.item(row, 2).text().strip()
        }
        first_added_row = -1
        for rule in DEFAULT_HIGHLIGHT_RULES:
            key = (rule.pattern, rule.case_sensitive, rule.regex)
            if key in existing:
                continue
            self._append_rule(rule)
            existing.add(key)
            if first_added_row < 0:
                first_added_row = self.table.rowCount() - 1
        if first_added_row >= 0:
            self.table.selectRow(first_added_row)

    def _append_rule(self, rule: HighlightRuleData):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setCellWidget(row, 0, self._check(rule.enabled))
        self.table.setItem(row, 1, QTableWidgetItem(rule.name))
        self.table.setItem(row, 2, QTableWidgetItem(rule.pattern))
        color_item = QTableWidgetItem(rule.color)
        color_item.setBackground(QColor(rule.color))
        color_item.setData(Qt.UserRole, rule.color)
        self.table.setItem(row, 3, color_item)
        self.table.setCellWidget(row, 4, self._check(rule.case_sensitive))
        self.table.setCellWidget(row, 5, self._check(rule.regex))

    def _check(self, checked: bool) -> QCheckBox:
        checkbox = QCheckBox()
        checkbox.setChecked(bool(checked))
        checkbox.setStyleSheet("margin-left: 8px;")
        return checkbox

    def _add_empty_rule(self):
        self._append_rule(HighlightRuleData("New Rule", "", "#fff3cd", False, False, True))
        self.table.selectRow(self.table.rowCount() - 1)

    def _add_rule_from_text(self, text: str):
        if not text:
            return
        colors = ["#ffec80", "#8cecff", "#a8f0a5", "#ffc078", "#c5a3ff", "#ff9ecb"]
        self._append_rule(
            HighlightRuleData(
                text[:32],
                text,
                colors[self.table.rowCount() % len(colors)],
                False,
                False,
                True,
            )
        )
        self.table.selectRow(self.table.rowCount() - 1)

    def _remove_selected_rule(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def _choose_color(self):
        row = self.table.currentRow()
        if row < 0:
            return
        current = self.table.item(row, 3)
        color = QColorDialog.getColor(QColor(current.data(Qt.UserRole) or "#fff3cd"), self, "Highlight Color")
        if not color.isValid():
            return
        value = color.name()
        current.setText(value)
        current.setData(Qt.UserRole, value)
        current.setBackground(color)

    def get_rules(self):
        rules = []
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 1)
            pattern_item = self.table.item(row, 2)
            color_item = self.table.item(row, 3)
            pattern = pattern_item.text().strip() if pattern_item else ""
            if not pattern:
                continue
            rules.append(
                HighlightRuleData(
                    name=name_item.text().strip() if name_item else "",
                    pattern=pattern,
                    color=color_item.data(Qt.UserRole) or color_item.text() or "#fff3cd",
                    case_sensitive=self.table.cellWidget(row, 4).isChecked(),
                    regex=self.table.cellWidget(row, 5).isChecked(),
                    enabled=self.table.cellWidget(row, 0).isChecked(),
                )
            )
        return rules
