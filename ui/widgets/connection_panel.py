from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDockWidget,
    QLabel,
    QMenu,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.remote_session_keys import is_remote_session_key, remote_session_server_id


class ConnectionPanel(QDockWidget):
    """Left dock that lists local, remote, network, and proxy sessions."""

    def __init__(self, parent, actions, snapshot_provider, activate_session, connect_session):
        super().__init__("Connections", parent)
        self.setObjectName("connectionPanelDock")
        self.setMinimumWidth(80)
        self._snapshot_provider = snapshot_provider
        self._activate_session = activate_session
        self._connect_session = connect_session
        self._actions = actions

        panel = QWidget(self)
        panel.setMinimumWidth(70)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        self._summary = QLabel(panel)
        self._summary.setWordWrap(True)
        layout.addWidget(self._summary)

        self._tree = QTreeWidget(panel)
        self._tree.setHeaderHidden(True)
        self._tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._tree.setTextElideMode(Qt.ElideNone)
        self._tree.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.itemClicked.connect(self._activate_item)
        self._tree.itemDoubleClicked.connect(self._connect_item)
        self._tree.itemActivated.connect(self._activate_item)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self._tree, 1)

        self.setWidget(panel)
        self.refresh()

    def refresh(self):
        snapshot = self._snapshot_provider()
        local_ports = []
        remote_ports = {}
        network_terms = []

        for session in snapshot.sessions:
            status = "Connected" if session.connected else "Disconnected"
            text = f"{session.name} [{status}]"
            if session.kind == "remote":
                server_id = remote_session_server_id(session.key) if is_remote_session_key(session.key) else ""
                remote_ports.setdefault(server_id or "Remote Server", []).append((session.key, text))
            elif session.kind == "network":
                network_terms.append((session.key, text))
            else:
                local_ports.append((session.key, text))

        self._tree.clear()
        self._add_group("Local", sorted(local_ports, key=lambda row: row[1]))
        self._add_remote_group(remote_ports)
        self._add_group("SSH/Telnet", sorted(network_terms, key=lambda row: row[1]))
        self._add_group("Proxy Clients", [(client, client) for client in snapshot.access.clients])
        self._tree.expandAll()
        self._tree.resizeColumnToContents(0)

        self._summary.setText(snapshot.access.summary)

    def _add_group(self, title, rows):
        group = QTreeWidgetItem([f"{title} ({len(rows)})"])
        group.setData(0, Qt.UserRole, None)
        self._tree.addTopLevelItem(group)
        for key, text in rows:
            item = QTreeWidgetItem([text])
            item.setData(0, Qt.UserRole, key)
            group.addChild(item)

    def _add_remote_group(self, remote_ports):
        count = sum(len(rows) for rows in remote_ports.values())
        group = QTreeWidgetItem([f"Remote ({count})"])
        group.setData(0, Qt.UserRole, None)
        self._tree.addTopLevelItem(group)
        for server_id in sorted(remote_ports):
            rows = sorted(remote_ports[server_id], key=lambda row: row[1])
            server_item = QTreeWidgetItem([f"{server_id} ({len(rows)})"])
            server_item.setData(0, Qt.UserRole, None)
            group.addChild(server_item)
            for key, text in rows:
                item = QTreeWidgetItem([text])
                item.setData(0, Qt.UserRole, key)
                server_item.addChild(item)

    def _activate_item(self, item, _column):
        key = item.data(0, Qt.UserRole)
        if key:
            self._activate_session(key)

    def _connect_item(self, item, _column):
        key = item.data(0, Qt.UserRole)
        if key:
            self._connect_session(key)

    def _show_context_menu(self, pos):
        menu = QMenu(self._tree)
        menu.addAction(self._actions.scan_ports)
        menu.addAction(self._actions.add_serial)
        menu.addAction(self._actions.access_settings)
        menu.addAction(self._actions.access_control)
        menu.exec_(self._tree.viewport().mapToGlobal(pos))
