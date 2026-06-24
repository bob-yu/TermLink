"""Dialog for creating local shell sessions."""

from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from core.local_shell_worker import LocalShellConfig, default_shell_command, shell_display_name


class LocalShellDialog(QDialog):
    """Local shell connection dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Local Shell")
        self.setMinimumWidth(460)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Optional tab name")
        form.addRow("Name:", self.name_edit)

        cwd_layout = QHBoxLayout()
        self.cwd_edit = QLineEdit()
        self.cwd_edit.setPlaceholderText("Optional working directory")
        cwd_layout.addWidget(self.cwd_edit, 1)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_working_directory)
        cwd_layout.addWidget(browse_btn)
        form.addRow("Working directory:", cwd_layout)

        self.encoding_edit = QLineEdit("utf-8")
        form.addRow("Encoding:", self.encoding_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_config(self) -> LocalShellConfig:
        command = default_shell_command()
        name = self.name_edit.text().strip()
        return LocalShellConfig(
            command=command,
            name=name or shell_display_name(command),
            working_directory=self.cwd_edit.text().strip(),
            encoding=self.encoding_edit.text().strip() or "utf-8",
        )

    def _browse_working_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Working Directory", "")
        if directory:
            self.cwd_edit.setText(directory)

    def _validate_and_accept(self):
        self.accept()
