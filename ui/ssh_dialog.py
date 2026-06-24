from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from core.ssh_worker import ConnectionType, RawTcpConfig, SSHConfig, SSHWorker, TelnetConfig


class SSHConnectDialog(QDialog):
    """SSH/Telnet/Raw TCP connection dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Network Connection")
        self.setMinimumWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        type_group = QGroupBox("Connection Type")
        type_layout = QHBoxLayout(type_group)

        self.type_combo = QComboBox()
        self.type_combo.addItem("SSH", ConnectionType.SSH)
        self.type_combo.addItem("Telnet", ConnectionType.TELNET)
        self.type_combo.addItem("Raw TCP", ConnectionType.RAW_TCP)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        type_layout.addWidget(self.type_combo)

        if not SSHWorker.is_available():
            self.type_combo.model().item(0).setEnabled(False)
            self.type_combo.setItemText(0, "SSH (requires paramiko)")

        layout.addWidget(type_group)

        conn_group = QGroupBox("Connection")
        conn_layout = QFormLayout(conn_group)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Optional tab name")
        conn_layout.addRow("Name:", self.name_edit)

        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText("IP address or host name")
        conn_layout.addRow("Host:", self.host_edit)

        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(22)
        conn_layout.addRow("Port:", self.port_spin)

        layout.addWidget(conn_group)

        auth_group = QGroupBox("Authentication")
        auth_layout = QFormLayout(auth_group)

        self.username_edit = QLineEdit()
        self.username_edit.setText("root")
        auth_layout.addRow("Username:", self.username_edit)

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        auth_layout.addRow("Password:", self.password_edit)

        key_layout = QHBoxLayout()
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("Optional SSH private key file")
        key_layout.addWidget(self.key_edit)

        self.key_btn = QPushButton("Browse...")
        self.key_btn.clicked.connect(self._browse_key_file)
        key_layout.addWidget(self.key_btn)

        self.key_label = QLabel("Key file:")
        auth_layout.addRow(self.key_label, key_layout)

        layout.addWidget(auth_group)
        self.auth_group = auth_group

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._on_type_changed(0)

    def _on_type_changed(self, _index):
        conn_type = self.type_combo.currentData()

        if conn_type == ConnectionType.SSH:
            self.port_spin.setValue(22)
            self.auth_group.setVisible(True)
            self.key_label.setVisible(True)
            self.key_edit.setVisible(True)
            self.key_btn.setVisible(True)
        elif conn_type == ConnectionType.TELNET:
            self.port_spin.setValue(23)
            self.auth_group.setVisible(True)
            self.key_label.setVisible(False)
            self.key_edit.setVisible(False)
            self.key_btn.setVisible(False)
        else:
            self.port_spin.setValue(2323)
            self.auth_group.setVisible(False)

    def _browse_key_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select SSH Private Key",
            "",
            "All files (*);;PEM files (*.pem);;Private keys (id_rsa id_ed25519)",
        )
        if filename:
            self.key_edit.setText(filename)

    def _validate_and_accept(self):
        if not self.host_edit.text().strip():
            QMessageBox.warning(self, "Error", "Enter a host address.")
            return

        conn_type = self.type_combo.currentData()
        if conn_type == ConnectionType.SSH:
            if not self.username_edit.text().strip():
                QMessageBox.warning(self, "Error", "SSH requires a username.")
                return
            if not self.password_edit.text() and not self.key_edit.text():
                QMessageBox.warning(self, "Error", "Enter a password or choose a key file.")
                return

        self.accept()

    def get_config(self):
        conn_type = self.type_combo.currentData()

        if conn_type == ConnectionType.SSH:
            return SSHConfig(
                host=self.host_edit.text().strip(),
                port=self.port_spin.value(),
                username=self.username_edit.text().strip(),
                password=self.password_edit.text(),
                key_file=self.key_edit.text().strip(),
                name=self.name_edit.text().strip(),
                connection_type=ConnectionType.SSH,
            )

        if conn_type == ConnectionType.TELNET:
            return TelnetConfig(
                host=self.host_edit.text().strip(),
                port=self.port_spin.value(),
                username=self.username_edit.text().strip(),
                password=self.password_edit.text(),
                name=self.name_edit.text().strip(),
                connection_type=ConnectionType.TELNET,
            )

        return RawTcpConfig(
            host=self.host_edit.text().strip(),
            port=self.port_spin.value(),
            name=self.name_edit.text().strip(),
            connection_type=ConnectionType.RAW_TCP,
        )
