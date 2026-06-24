from PyQt5.QtWidgets import QAction

try:
    from .icon_provider import icon
except ImportError:  # pragma: no cover - used by lightweight action tests
    def icon(_name):
        return None


class MainWindowActions:
    """Shared QAction registry for toolbar, menus, and dock panels."""

    def __init__(self, window):
        self.scan_ports = self._action(window, "Scan Ports", "Ctrl+R", window._scan_and_connect_all, "scan")
        self.add_serial = self._action(window, "Serial", "Ctrl+N", window._add_serial_port, "connection-serial")
        self.connect_all = self._action(window, "Connect All", None, window._connect_all, "plug-connect")
        self.disconnect_all = self._action(window, "Disconnect All", None, window._disconnect_all, "plug-disconnect")

        self.download_logs = self._action(window, "Download Server Logs", None, window._remote_log_download.show, "download")
        self.exit_app = self._action(window, "Exit", "Alt+F4", window.close, "x")

        self.add_ssh = self._action(window, "SSH", "Ctrl+Shift+S", window._add_ssh_connection, "connection-ssh")
        self.add_telnet = self._action(window, "Telnet", "Ctrl+Shift+T", window._add_telnet_connection, "connection-telnet")
        self.add_raw_tcp = self._action(window, "Raw TCP", None, window._add_raw_tcp_connection, "terminal")
        self.add_remote_serial = self._action(window, "Remote Serial", None, window._add_remote_serial_connection, "network")

        self.scan_patterns = self._action(window, "Scan Patterns", None, window._scan_pattern_settings.show, "search")
        self.access_settings = self._action(window, "Serial Remote Access Settings", None, window._set_network_config, "network")
        self.access_control = self._action(window, "Serial Remote Access Control", None, window._show_serial_remote_access_control, "network")
        self.terminal_settings = self._action(window, "Terminal Settings", None, window._terminal_settings.show, "terminal-gear")

        self.changelog = self._action(window, "Changelog", None, window._show_changelog, "info")
        self.open_docs = self._action(window, "Documentation", "F1", window._open_documentation, "book-open")
        self.about = self._action(window, "About", None, window._show_about, "circle-help")

    @staticmethod
    def _action(parent, text, shortcut, callback, icon_key=None):
        action = QAction(text, parent)
        if shortcut:
            action.setShortcut(shortcut)
        action_icon = icon(icon_key) if icon_key else None
        if action_icon is not None and hasattr(action, "setIcon"):
            action.setIcon(action_icon)
        if hasattr(action, "setToolTip"):
            action.setToolTip(f"{text} ({shortcut})" if shortcut else text)
        if hasattr(action, "setStatusTip"):
            action.setStatusTip(text)
        action.triggered.connect(callback)
        return action
