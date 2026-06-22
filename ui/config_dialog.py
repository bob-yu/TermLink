import glob
import platform

from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from core.serial_worker import SerialWorker
from utils.config_schema import PortConfigData


class ConfigDialog(QDialog):
    """Serial port configuration dialog."""

    def __init__(self, port_config: PortConfigData = None, parent=None):
        super().__init__(parent)
        self.port_config = port_config
        self.setWindowTitle("Serial Port Settings")
        self.setMinimumWidth(450)
        self._setup_ui()

        if port_config:
            self._load_config(port_config)

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        basic_group = QGroupBox("Serial Port")
        basic_layout = QFormLayout(basic_group)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Optional device name")
        basic_layout.addRow("Name:", self.name_edit)

        port_layout = QHBoxLayout()
        self.port_combo = QComboBox()
        self.port_combo.setEditable(True)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._refresh_ports)
        port_layout.addWidget(self.port_combo)
        port_layout.addWidget(self.refresh_btn)
        basic_layout.addRow("Serial port:", port_layout)

        self.baudrate_combo = QComboBox()
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
        self.baudrate_combo.setCurrentText("115200")
        basic_layout.addRow("Baudrate:", self.baudrate_combo)

        self.data_bits_combo = QComboBox()
        self.data_bits_combo.addItems(["5", "6", "7", "8"])
        self.data_bits_combo.setCurrentText("8")
        basic_layout.addRow("Data bits:", self.data_bits_combo)

        self.parity_combo = QComboBox()
        self.parity_combo.addItem("None", "N")
        self.parity_combo.addItem("Even", "E")
        self.parity_combo.addItem("Odd", "O")
        self.parity_combo.addItem("Mark", "M")
        self.parity_combo.addItem("Space", "S")
        basic_layout.addRow("Parity:", self.parity_combo)

        self.stop_bits_combo = QComboBox()
        self.stop_bits_combo.addItem("1", 1.0)
        self.stop_bits_combo.addItem("1.5", 1.5)
        self.stop_bits_combo.addItem("2", 2.0)
        basic_layout.addRow("Stop bits:", self.stop_bits_combo)

        self.flow_control_combo = QComboBox()
        self.flow_control_combo.addItem("None", "none")
        self.flow_control_combo.addItem("XON/XOFF", "xonxoff")
        self.flow_control_combo.addItem("RTS/CTS", "rtscts")
        self.flow_control_combo.addItem("DSR/DTR", "dsrdtr")
        basic_layout.addRow("Flow control:", self.flow_control_combo)

        layout.addWidget(basic_group)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self._refresh_ports()

    def _refresh_ports(self):
        current = self.port_combo.currentText()
        self.port_combo.clear()

        ports = SerialWorker.list_ports()
        if platform.system() == "Linux":
            linux_ports = []
            patterns = [
                "/dev/ttyUSB*",
                "/dev/ttyACM*",
                "/dev/ttyS*",
                "/dev/ttyAMA*",
                "/dev/ttyTHS*",
            ]
            for pattern in patterns:
                linux_ports.extend(glob.glob(pattern))
            ports = list(set(ports + linux_ports))
            ports.sort()

        self.port_combo.addItems(ports)

        if current:
            index = self.port_combo.findText(current)
            if index >= 0:
                self.port_combo.setCurrentIndex(index)
            else:
                self.port_combo.setEditText(current)

    def _load_config(self, config: PortConfigData):
        self.name_edit.setText(config.name)
        self.port_combo.setEditText(config.port)
        self.baudrate_combo.setCurrentText(str(config.baudrate))
        self.data_bits_combo.setCurrentText(str(config.data_bits))
        self._set_combo_by_data(self.parity_combo, config.parity)
        self._set_combo_by_data(self.stop_bits_combo, config.stop_bits)
        self._set_combo_by_data(self.flow_control_combo, config.flow_control)

    def _on_accept(self):
        port = self.port_combo.currentText().strip()
        if not port:
            QMessageBox.warning(self, "Error", "Select or enter a serial port.")
            return

        self.accept()

    def get_config(self) -> PortConfigData:
        return PortConfigData(
            name=self.name_edit.text() or self.port_combo.currentText(),
            port=self.port_combo.currentText(),
            baudrate=int(self.baudrate_combo.currentText()),
            data_bits=int(self.data_bits_combo.currentText()),
            parity=self.parity_combo.currentData(),
            stop_bits=float(self.stop_bits_combo.currentData()),
            flow_control=self.flow_control_combo.currentData(),
        )

    @staticmethod
    def _set_combo_by_data(combo: QComboBox, value):
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)
