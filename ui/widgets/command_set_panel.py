from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QDockWidget,
    QFormLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from utils.config_schema import CommandSetData


class CommandSetDialog(QDialog):
    """Editor for one named command set."""

    def __init__(self, parent=None, command_set=None):
        super().__init__(parent)
        self.setWindowTitle("Command Set")
        self.setMinimumSize(420, 320)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit(self)
        self.commands_edit = QPlainTextEdit(self)
        self.commands_edit.setPlaceholderText("One command per line")

        if command_set:
            self.name_edit.setText(command_set.name)
            self.commands_edit.setPlainText("\n".join(command_set.commands))

        form.addRow("Name", self.name_edit)
        form.addRow("Commands", self.commands_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_command_set(self):
        name = self.name_edit.text().strip()
        commands = [
            line.strip()
            for line in self.commands_edit.toPlainText().splitlines()
            if line.strip()
        ]
        return CommandSetData(name=name, commands=commands)

    def accept(self):
        command_set = self.get_command_set()
        if not command_set.name:
            QMessageBox.warning(self, "Warning", "Command set name is required.")
            return
        if not command_set.commands:
            QMessageBox.warning(self, "Warning", "At least one command is required.")
            return
        super().accept()


class CommandSetPanel(QDockWidget):
    """Right dock for managing and running named command groups."""

    def __init__(self, parent, command_sets_provider, save_callback, run_callback):
        super().__init__("Command Sets", parent)
        self.setObjectName("commandSetDock")
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.setMinimumWidth(45)
        self._command_sets_provider = command_sets_provider
        self._save_callback = save_callback
        self._run_callback = run_callback

        panel = QWidget(self)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(0)

        self._list = QListWidget(panel)
        self._list.setSelectionMode(QAbstractItemView.SingleSelection)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._list.setTextElideMode(Qt.ElideNone)
        self._list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._list.itemDoubleClicked.connect(lambda _item: self._run_selected())
        self._list.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self._list, 1)

        self.setWidget(panel)
        self.refresh()

    def refresh(self):
        self._list.clear()
        for index, command_set in enumerate(self._command_sets_provider()):
            item = QListWidgetItem(command_set.name)
            item.setToolTip("\n".join(command_set.commands))
            item.setData(Qt.UserRole, index)
            self._list.addItem(item)

    def _selected_index(self):
        item = self._list.currentItem()
        if not item:
            return None
        return item.data(Qt.UserRole)

    def _add(self):
        dialog = CommandSetDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return
        self._command_sets_provider().append(dialog.get_command_set())
        self._save_callback()
        self.refresh()

    def _edit_selected(self):
        index = self._selected_index()
        if index is None:
            return
        command_sets = self._command_sets_provider()
        dialog = CommandSetDialog(self, command_sets[index])
        if dialog.exec_() != QDialog.Accepted:
            return
        command_sets[index] = dialog.get_command_set()
        self._save_callback()
        self.refresh()
        self._list.setCurrentRow(index)

    def _delete_selected(self):
        index = self._selected_index()
        if index is None:
            return
        command_sets = self._command_sets_provider()
        name = command_sets[index].name
        confirmed = QMessageBox.question(
            self,
            "Delete Command Set",
            f"Delete command set '{name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirmed != QMessageBox.Yes:
            return
        del command_sets[index]
        self._save_callback()
        self.refresh()

    def _run_selected(self):
        index = self._selected_index()
        if index is None:
            return
        command_set = self._command_sets_provider()[index]
        self._run_callback(command_set)

    def _show_context_menu(self, pos):
        menu = QMenu(self._list)
        menu.addAction("Run", self._run_selected)
        menu.addSeparator()
        menu.addAction("Add", self._add)
        menu.addAction("Edit", self._edit_selected)
        menu.addAction("Delete", self._delete_selected)
        menu.exec_(self._list.viewport().mapToGlobal(pos))
