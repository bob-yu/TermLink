from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QSizePolicy,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class SerialPortPickerDialog(QDialog):
    def __init__(
        self,
        ports,
        connected_ports,
        parent=None,
        port_labels=None,
        default_baudrate=115200,
    ):
        super().__init__(parent)
        self.setWindowTitle("Select Serial Ports")
        self.setMinimumSize(780, 560)
        self.resize(940, 640)
        self._checkboxes = []
        port_labels = port_labels or {}

        layout = QVBoxLayout(self)

        settings_group = QGroupBox("Settings for selected ports", self)
        settings_layout = QFormLayout(settings_group)

        self.baudrate_combo = QComboBox(settings_group)
        self.baudrate_combo.setEditable(True)
        self.baudrate_combo.addItems([
            "9600",
            "19200",
            "38400",
            "57600",
            "115200",
            "230400",
            "460800",
            "921600",
        ])
        self.baudrate_combo.setCurrentText(str(default_baudrate))
        settings_layout.addRow("Baudrate:", self.baudrate_combo)

        self.data_bits_combo = QComboBox(settings_group)
        self.data_bits_combo.addItems(["5", "6", "7", "8"])
        self.data_bits_combo.setCurrentText("8")
        settings_layout.addRow("Data bits:", self.data_bits_combo)

        self.parity_combo = QComboBox(settings_group)
        self.parity_combo.addItem("None", "N")
        self.parity_combo.addItem("Even", "E")
        self.parity_combo.addItem("Odd", "O")
        self.parity_combo.addItem("Mark", "M")
        self.parity_combo.addItem("Space", "S")
        settings_layout.addRow("Parity:", self.parity_combo)

        self.stop_bits_combo = QComboBox(settings_group)
        self.stop_bits_combo.addItem("1", 1.0)
        self.stop_bits_combo.addItem("1.5", 1.5)
        self.stop_bits_combo.addItem("2", 2.0)
        settings_layout.addRow("Stop bits:", self.stop_bits_combo)

        self.flow_control_combo = QComboBox(settings_group)
        self.flow_control_combo.addItem("None", "none")
        self.flow_control_combo.addItem("XON/XOFF", "xonxoff")
        self.flow_control_combo.addItem("RTS/CTS", "rtscts")
        self.flow_control_combo.addItem("DSR/DTR", "dsrdtr")
        settings_layout.addRow("Flow control:", self.flow_control_combo)

        layout.addWidget(settings_group)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_widget = QWidget(scroll)
        scroll_layout = QVBoxLayout(scroll_widget)

        for port in ports:
            already_connected = port in connected_ports
            label = port_labels.get(port, port)
            checkbox = QCheckBox(label, scroll_widget)
            checkbox.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            checkbox.setMinimumWidth(900)
            if already_connected:
                checkbox.setText(f"{label} (connected)")
                checkbox.setEnabled(False)
            else:
                checkbox.setChecked(True)
            self._checkboxes.append((checkbox, port))
            scroll_layout.addWidget(checkbox)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        button_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All", self)
        select_all_btn.clicked.connect(self._select_all)
        deselect_all_btn = QPushButton("Clear Selection", self)
        deselect_all_btn.clicked.connect(self._deselect_all)
        button_layout.addWidget(select_all_btn)
        button_layout.addWidget(deselect_all_btn)
        layout.addLayout(button_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self):
        try:
            int(self.baudrate_combo.currentText())
        except ValueError:
            QMessageBox.warning(self, "Error", "Enter a valid baudrate.")
            return
        super().accept()

    def selected_ports(self):
        return [port for checkbox, port in self._checkboxes if checkbox.isChecked()]

    def serial_settings(self):
        return {
            "baudrate": int(self.baudrate_combo.currentText()),
            "data_bits": int(self.data_bits_combo.currentText()),
            "parity": self.parity_combo.currentData(),
            "stop_bits": float(self.stop_bits_combo.currentData()),
            "flow_control": self.flow_control_combo.currentData(),
        }

    def _select_all(self):
        for checkbox, _port in self._checkboxes:
            if checkbox.isEnabled():
                checkbox.setChecked(True)

    def _deselect_all(self):
        for checkbox, _port in self._checkboxes:
            if checkbox.isEnabled():
                checkbox.setChecked(False)
