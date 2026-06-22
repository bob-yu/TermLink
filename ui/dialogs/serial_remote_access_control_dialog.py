import time

from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.serial_access_permissions import PERMISSION_READ_ONLY, PERMISSION_READ_WRITE


class SerialRemoteAccessControlDialog(QDialog):
    def __init__(self, server, config, save_config, parent=None):
        super().__init__(parent)
        self._server = server
        self._config = config
        self._save_config = save_config
        self.setWindowTitle("Serial Remote Access Control")
        self.resize(920, 520)
        self.setMinimumSize(760, 420)

        layout = QVBoxLayout(self)
        if not server:
            layout.addWidget(QLabel("Serial remote access server is not running.", self))
            buttons = QDialogButtonBox(QDialogButtonBox.Close, self)
            buttons.rejected.connect(self.reject)
            layout.addWidget(buttons)
            return

        splitter = QSplitter(self)
        splitter.addWidget(self._build_client_panel())
        splitter.addWidget(self._build_ban_panel())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close, self)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.refresh()

    def _build_client_panel(self):
        panel = QWidget(self)
        layout = QVBoxLayout(panel)
        layout.addWidget(QLabel("Connected clients", panel))

        self.client_table = QTableWidget(0, 8, panel)
        self.client_table.setHorizontalHeaderLabels([
            "Client",
            "IP",
            "Permission",
            "Authorized",
            "Ports",
            "Last active",
            "Reads",
            "Writes",
        ])
        self.client_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.client_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.client_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.client_table, 1)

        row = QHBoxLayout()
        refresh_btn = QPushButton("Refresh", panel)
        refresh_btn.clicked.connect(self.refresh)
        disconnect_btn = QPushButton("Disconnect", panel)
        disconnect_btn.clicked.connect(self._disconnect_selected)
        ban_btn = QPushButton("Ban IP", panel)
        ban_btn.clicked.connect(self._ban_selected)
        readonly_btn = QPushButton("Set Read-only", panel)
        readonly_btn.clicked.connect(lambda: self._set_permission(PERMISSION_READ_ONLY))
        readwrite_btn = QPushButton("Set Read/Write", panel)
        readwrite_btn.clicked.connect(lambda: self._set_permission(PERMISSION_READ_WRITE))
        row.addWidget(refresh_btn)
        row.addWidget(disconnect_btn)
        row.addWidget(ban_btn)
        row.addWidget(readonly_btn)
        row.addWidget(readwrite_btn)
        row.addStretch()
        layout.addLayout(row)
        return panel

    def _build_ban_panel(self):
        panel = QWidget(self)
        layout = QVBoxLayout(panel)
        layout.addWidget(QLabel("Banned IPs", panel))
        self.banned_list = QListWidget(panel)
        layout.addWidget(self.banned_list, 1)

        add_row = QHBoxLayout()
        self.banned_ip_edit = QLineEdit(panel)
        self.banned_ip_edit.setPlaceholderText("IP address")
        self.banned_ip_edit.returnPressed.connect(self._add_banned_ip)
        add_btn = QPushButton("Add", panel)
        add_btn.clicked.connect(self._add_banned_ip)
        add_row.addWidget(self.banned_ip_edit, 1)
        add_row.addWidget(add_btn)
        layout.addLayout(add_row)

        row = QHBoxLayout()
        unban_btn = QPushButton("Unban", panel)
        unban_btn.clicked.connect(self._unban_selected)
        row.addWidget(unban_btn)
        row.addStretch()
        layout.addLayout(row)
        return panel

    def refresh(self):
        infos = self._server.client_infos()
        self.client_table.setRowCount(len(infos))
        now = time.time()
        for row, info in enumerate(infos):
            ports = ", ".join(info.opened_ports or ([info.selected_port] if info.selected_port else []))
            values = [
                info.address,
                info.ip,
                info.permission,
                "Yes" if info.authorized else "No",
                ports,
                self._format_age(now - info.last_active_at),
                str(info.read_count),
                str(info.write_count),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(32, info.address)
                item.setData(33, info.ip)
                self.client_table.setItem(row, col, item)
        self.client_table.resizeColumnsToContents()

        self.banned_list.clear()
        for ip in self._server.banned_ips:
            self.banned_list.addItem(QListWidgetItem(ip))

    def _selected_client(self):
        row = self.client_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Serial Remote Access Control", "Select a client first.")
            return None, None
        item = self.client_table.item(row, 0)
        return item.data(32), item.data(33)

    def _disconnect_selected(self):
        addr, _ip = self._selected_client()
        if not addr:
            return
        self._server.disconnect_client(addr)
        self.refresh()

    def _ban_selected(self):
        addr, ip = self._selected_client()
        if not addr or not ip:
            return
        self._server.ban_ip(ip, disconnect=True)
        self._persist_banned_ips()
        self.refresh()

    def _set_permission(self, permission):
        addr, _ip = self._selected_client()
        if not addr:
            return
        self._server.set_client_permission(addr, permission)
        self.refresh()

    def _unban_selected(self):
        item = self.banned_list.currentItem()
        if not item:
            QMessageBox.information(self, "Serial Remote Access Control", "Select a banned IP first.")
            return
        self._server.unban_ip(item.text())
        self._persist_banned_ips()
        self.refresh()

    def _add_banned_ip(self):
        ip = self.banned_ip_edit.text().strip()
        if not ip:
            QMessageBox.information(self, "Serial Remote Access Control", "Enter an IP address first.")
            return
        if self._server.ban_ip(ip, disconnect=True):
            self.banned_ip_edit.clear()
            self._persist_banned_ips()
            self.refresh()

    def _persist_banned_ips(self):
        self._config.serial_access_banned_ips = self._server.banned_ips
        self._save_config()

    @staticmethod
    def _format_age(seconds):
        seconds = max(0, int(seconds))
        if seconds < 60:
            return f"{seconds}s ago"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes}m ago"
        return f"{minutes // 60}h ago"
