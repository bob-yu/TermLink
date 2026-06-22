from dataclasses import dataclass

from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QComboBox,
    QSpinBox,
    QVBoxLayout,
)


@dataclass
class SerialAccessSettings:
    host: str
    port: int
    access_enabled: bool
    access_password: str
    max_clients: int
    default_permission: str


class SerialAccessSettingsDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Serial Remote Access Settings")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)

        server_group = QGroupBox("Serial Remote Access Server", self)
        server_layout = QFormLayout(server_group)
        self.access_enabled_cb = QCheckBox("Enable local serial access server", server_group)
        self.access_enabled_cb.setChecked(
            config.serial_access_enabled or config.serial_access_mode == "server"
        )
        self.host_edit = QLineEdit(config.serial_access_host, server_group)
        self.host_edit.setPlaceholderText("0.0.0.0 listens on all network interfaces")
        self.port_spin = QSpinBox(server_group)
        self.port_spin.setRange(1024, 65535)
        self.port_spin.setValue(config.serial_access_port)
        self.access_password_edit = QLineEdit(config.serial_access_password, server_group)
        self.access_password_edit.setEchoMode(QLineEdit.Password)
        self.access_password_edit.setPlaceholderText("Leave empty to disable password protection")
        self.show_password_cb = QCheckBox("Show password", server_group)
        self.show_password_cb.toggled.connect(self._toggle_password_visible)
        self.max_clients_spin = QSpinBox(server_group)
        self.max_clients_spin.setRange(1, 128)
        self.max_clients_spin.setValue(getattr(config, "serial_access_max_clients", 16))
        self.default_permission_combo = QComboBox(server_group)
        self.default_permission_combo.addItem("Read / Write", "read-write")
        self.default_permission_combo.addItem("Read only", "read-only")
        default_permission = getattr(config, "serial_access_default_permission", "read-write")
        index = self.default_permission_combo.findData(default_permission)
        self.default_permission_combo.setCurrentIndex(index if index >= 0 else 0)
        server_layout.addRow(self.access_enabled_cb)
        server_layout.addRow("Listen address:", self.host_edit)
        server_layout.addRow("Port:", self.port_spin)
        server_layout.addRow("Max clients:", self.max_clients_spin)
        server_layout.addRow("Default permission:", self.default_permission_combo)
        server_layout.addRow("Access password:", self.access_password_edit)
        server_layout.addRow("", self.show_password_cb)
        layout.addWidget(server_group)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_settings(self) -> SerialAccessSettings:
        return SerialAccessSettings(
            host=self.host_edit.text(),
            port=self.port_spin.value(),
            access_enabled=self.access_enabled_cb.isChecked(),
            access_password=self.access_password_edit.text(),
            max_clients=self.max_clients_spin.value(),
            default_permission=self.default_permission_combo.currentData(),
        )

    def _toggle_password_visible(self, visible: bool):
        self.access_password_edit.setEchoMode(
            QLineEdit.Normal if visible else QLineEdit.Password
        )
