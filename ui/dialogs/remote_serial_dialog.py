from dataclasses import dataclass

from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from utils.config_schema import DEFAULT_REMOTE_SERIAL_PORT


@dataclass
class RemoteSerialConnectionSettings:
    server_address: str
    access_password: str


class RemoteSerialDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Remote Serial")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.server_addr_edit = QLineEdit(config.serial_access_server_address, self)
        self.server_addr_edit.setPlaceholderText(
            f"Server address, for example 192.168.1.100:{DEFAULT_REMOTE_SERIAL_PORT}"
        )
        self.access_password_edit = QLineEdit(
            getattr(config, "serial_access_client_password", config.serial_access_password),
            self,
        )
        self.access_password_edit.setEchoMode(QLineEdit.Password)
        self.access_password_edit.setPlaceholderText("Password, if required")
        self.show_password_cb = QCheckBox("Show password", self)
        self.show_password_cb.toggled.connect(self._toggle_password_visible)

        form.addRow("Server address:", self.server_addr_edit)
        form.addRow("Access password:", self.access_password_edit)
        form.addRow("", self.show_password_cb)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_settings(self):
        return RemoteSerialConnectionSettings(
            server_address=self.server_addr_edit.text().strip(),
            access_password=self.access_password_edit.text(),
        )

    def accept(self):
        if not self.server_addr_edit.text().strip():
            QMessageBox.warning(self, "Warning", "Server address is required.")
            return
        super().accept()

    def _toggle_password_visible(self, visible: bool):
        self.access_password_edit.setEchoMode(
            QLineEdit.Normal if visible else QLineEdit.Password
        )
