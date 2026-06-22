"""

主窗口模块

应用程序的主界面

"""

import platform

import glob

import os

from PyQt5.QtWidgets import (

    QMainWindow, QTabWidget,

    QMessageBox, QStatusBar,

    QInputDialog, QDialog, QVBoxLayout, QDialogButtonBox,

    QWidget, QShortcut

)

from PyQt5.QtCore import Qt, QTimer, QUrl, QByteArray

from PyQt5.QtGui import QDesktopServices, QKeySequence

from typing import Dict, List

from core.serial_worker import SerialWorker

from core.device_info_parser import parse_ip_from_ifconfig

from utils.config_manager import ConfigManager
from utils.config_schema import (
    PortConfigData,
    LoginConfigData,
)

from .actions import MainWindowActions
from .connection_snapshot import AccessSnapshot, ConnectionSnapshot, SessionSnapshot
from .icon_provider import icon
from .session_config_selector import serial_port_configs_to_save
from .toolbar_builder import build_main_toolbar

from .controllers import (
    LocalSerialSessionController,
    RemoteLogDownloadController,
    HighlightRulesController,
    ScanPatternSettingsController,
    SessionController,
    TerminalSettingsController,
    RemoteSerialSessionController,
    SerialAccessController,
)
from .widgets import CommandSetPanel, ConnectionPanel, RuntimeLogPanel

from core.serial_access_server import SerialAccessMode

from core.remote_session_keys import is_remote_session_key, remote_session_server_id

from core.log_manager import LogManager
from core.remote_server_manager import RemoteServerManager

class MainWindow(QMainWindow):

    """

    主窗口

    功能:

    - 管理多个串口会话

    - 工具栏操作

    - 配置管理

    """

    def __init__(self):

        super().__init__()

        self.setWindowTitle("TermLink")

        self.setMinimumSize(900, 600)
        self.resize(1500, 920)

        # 配置管理器

        self.config_manager = ConfigManager()

        self.app_config = self.config_manager.load()

        # 日志管理器

        self._log_manager = LogManager(

            log_dir=self.app_config.log_dir,

            name_pattern=self.app_config.log_name_pattern,

            max_days=self.app_config.log_max_days,

            max_total_size_mb=self.app_config.log_max_total_size_mb,

            max_file_size_mb=self.app_config.log_max_file_size_mb,

            auto_clean=self.app_config.log_auto_clean,

        )

        # 启动时异步清理过期日志

        self._log_manager.cleanup_async()

        # 串口会话管理

        self._sessions: Dict[str, tuple] = {}  # port -> (worker, tab)

        self._session_controller = SessionController(self._sessions)

        self._remote_log_download = RemoteLogDownloadController(self)

        self._local_serial_sessions = LocalSerialSessionController(self)
        self._network_terminal_sessions = None
        self._highlight_rules = HighlightRulesController(self)
        self._terminal_settings = TerminalSettingsController(self)
        self._scan_pattern_settings = ScanPatternSettingsController(self)
        self._remote_serial_sessions = RemoteSerialSessionController(self)
        self._serial_access_controller = SerialAccessController(self)

        # 网络服务（服务端/客户端）

        self._network_server = None

        self._network_client = None
        self._remote_clients = RemoteServerManager()

        self._network_mode = SerialAccessMode.DISABLED

        self._serial_access_server = None

        # 默认登录配置（用于扫描自动连接）

        self._default_login = LoginConfigData(

            username="root",

            password="root",

            login_prompt="login:",

            password_prompt="Password:",

            shell_prompt=["#", "$"]

        )

        self._default_baudrate = 115200

        self._default_auto_commands = []

        self._default_keywords = {

            "error": ["error", "Error", "ERROR"],

            "panic": ["panic", "Panic", "PANIC"],

            "warning": ["warning", "Warning", "WARNING"]

        }

        self._setup_ui()

        self.actions = MainWindowActions(self)

        self._setup_menubar()

        self._setup_docks()

        self._setup_toolbar()

        self._setup_statusbar()

        self._restore_user_preferences()

        # 加载已保存的串口配置

        self._load_saved_ports()

        # 初始化网络

        self._init_network()

    def _setup_tab_shortcuts(self):

        """设置 Alt+数字 快捷键切换标签页"""

        for i in range(1, 10):  # Alt+1 到 Alt+9

            shortcut = QShortcut(QKeySequence(f"Alt+{i}"), self)

            shortcut.activated.connect(lambda idx=i-1: self._switch_to_tab(idx))

        # Alt+0 切换到第10个标签

        shortcut = QShortcut(QKeySequence("Alt+0"), self)

        shortcut.activated.connect(lambda: self._switch_to_tab(9))

    def _switch_to_tab(self, index: int):

        """切换到指定标签页"""

        if 0 <= index < self.tab_widget.count():

            self.tab_widget.setCurrentIndex(index)

    def _on_tab_changed(self, index: int):

        """标签页切换时刷新当前标签页"""

        self._sync_watch_dialog_visibility(index)

        if index >= 0:

            tab = self.tab_widget.widget(index)

            if hasattr(tab, 'terminal'):

                # 强制刷新当前标签页的终端

                tab.terminal._view._buffer_dirty = True

                tab.terminal._view.update()

                tab.terminal.setFocus()

    def _sync_watch_dialog_visibility(self, current_index: int):
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if not hasattr(tab, "terminal"):
                continue
            if i == current_index:
                tab.terminal.show_watch_if_active()
            else:
                tab.terminal.hide_watch_dialog()

    def _setup_ui(self):

        """设置UI"""

        # 标签页容器

        self.tab_widget = QTabWidget()

        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                border-top: 1px solid #d8dee4;
            }
            QTabBar::tab {
                background: #f1f5f9;
                border: 1px solid #d8dee4;
                border-bottom: none;
                color: #24292f;
                padding: 6px 28px 6px 10px;
                min-height: 22px;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                border-top: 2px solid #0969da;
            }
            QTabBar::tab:hover:!selected {
                background: #eef2f7;
            }
            QTabBar::close-button {
                image: url(ui/resources/icons/x.svg);
                subcontrol-position: right;
                width: 14px;
                height: 14px;
                margin-right: 7px;
            }
            QTabBar::close-button:hover {
                background: #e2e8f0;
                border-radius: 4px;
            }
        """)

        self.tab_widget.tabCloseRequested.connect(self._close_tab)

        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        self.setCentralWidget(self.tab_widget)

    def _setup_docks(self):

        """设置主要停靠面板"""

        self.runtime_log_panel = RuntimeLogPanel(self)

        self.addDockWidget(Qt.BottomDockWidgetArea, self.runtime_log_panel)
        self.runtime_log_panel.visibilityChanged.connect(self._apply_dock_corner_policy)
        self._apply_dock_corner_policy()

        self.connection_panel = ConnectionPanel(
            self,
            self.actions,
            self._build_connection_snapshot,
            self._activate_session,
            self._connect_session,
        )

        self.addDockWidget(Qt.LeftDockWidgetArea, self.connection_panel)

        self.command_set_panel = CommandSetPanel(
            self,
            lambda: self.app_config.command_sets,
            self.config_manager.save,
            self._run_command_set,
        )

        self.addDockWidget(Qt.RightDockWidgetArea, self.command_set_panel)

        if not getattr(self.app_config, "window_state", ""):

            self.runtime_log_panel.hide()

            self.command_set_panel.hide()

        self._apply_dock_corner_policy()

    def _apply_dock_corner_policy(self):

        """Keep side docks aligned with the central tab area above bottom docks."""

        bottom_left_area = (
            Qt.BottomDockWidgetArea
            if getattr(self, "runtime_log_panel", None) and self.runtime_log_panel.isVisible()
            else Qt.LeftDockWidgetArea
        )
        self.setCorner(Qt.BottomLeftCorner, bottom_left_area)
        self.setCorner(Qt.BottomRightCorner, Qt.BottomDockWidgetArea)

    def _refresh_connection_panel(self):

        panel = getattr(self, "connection_panel", None)

        if panel:

            panel.refresh()

    def _build_connection_snapshot(self):

        sessions = []

        for key, (worker, _tab, config) in self._sessions.items():

            name = config.name if config and config.name else key

            if is_remote_session_key(key):

                kind = "remote"

            elif key.startswith("ssh://") or key.startswith("telnet://"):

                kind = "network"

            else:

                kind = "local"

            sessions.append(SessionSnapshot(
                key=key,
                name=name,
                connected=getattr(worker, "is_connected", False),
                kind=kind,
            ))

        connected = sum(1 for session in sessions if session.connected)

        return ConnectionSnapshot(
            sessions=sessions,
            access=AccessSnapshot(
                summary=f"Sessions: {len(sessions)}, connected: {connected}",
                details=self._serial_access_detail_lines(),
                clients=self._network_server.client_port_labels if self._network_server else [],
            ),
        )

    def _serial_access_detail_lines(self):

        details = []

        if self._network_server:

            details.append(f"Remote access server: {self.app_config.serial_access_host}:{self.app_config.serial_access_port}")

        else:

            details.append("Remote access server: disabled")

        remote_client_ids = list(self._remote_clients.server_ids())
        if remote_client_ids:

            details.append(f"Connected remote servers: {', '.join(remote_client_ids)}")

        if self._serial_access_server and self._serial_access_server.is_running:

            details.append("Automation API: enabled")

        elif self.app_config.serial_access_enabled:

            details.append("Automation API: waiting for remote access server")

        else:

            details.append("Automation API: disabled")

        if self.app_config.serial_access_password:

            details.append("Access control: password enabled")

        else:

            details.append("Access control: no password")

        return details

    def _activate_session(self, key: str):

        if key not in self._sessions:

            return

        worker, tab, _config = self._sessions[key]

        index = self.tab_widget.indexOf(tab)

        if index >= 0:

            self.tab_widget.setCurrentIndex(index)

    def _connect_session(self, key: str):

        if key not in self._sessions:

            return

        worker, tab, _config = self._sessions[key]

        index = self.tab_widget.indexOf(tab)

        if index >= 0:

            self.tab_widget.setCurrentIndex(index)

        if hasattr(worker, "is_connected") and not worker.is_connected and hasattr(worker, "start"):

            worker.start()

            self._refresh_connection_panel()

            self.statusbar.showMessage(f"Connecting: {key}")

    def _set_tab_title(self, tab: QWidget, title: str):

        index = self.tab_widget.indexOf(tab)

        if index >= 0:

            self.tab_widget.setTabText(index, title)

    def _setup_menubar(self):

        """Keep actions available without showing a traditional menu bar."""
        self._download_logs_action = self.actions.download_logs
        self._download_logs_action.setVisible(False)
        self.menuBar().hide()

    def _open_documentation(self):

        """Open generated HTML documentation in the system browser."""

        from utils.docs_builder import build_documentation

        try:

            index_path = build_documentation()

            if not index_path.exists():

                QMessageBox.warning(self, "Documentation", "Documentation index was not generated.")

                return

            QDesktopServices.openUrl(QUrl.fromLocalFile(str(index_path)))

        except Exception as exc:

            QMessageBox.warning(self, "Documentation", f"Failed to open documentation: {exc}")

    def _show_about(self):

        """显示关于对话框"""

        about_text = """

<h2>TermLink v1.0.5</h2>

<p>Serial terminal, proxy, and remote serial access tool.</p>

<h3>Features</h3>

<ul>

<li>Manage multiple serial sessions</li>

<li>Optional login and command automation</li>

<li>VT100/xterm terminal emulation</li>

<li>Remote serial access for server and client workflows</li>

<li>SSH/Telnet connections</li>

<li>Runtime logs and remote log download</li>

<li>SysRq support</li>

</ul>

<h3>Shortcuts</h3>

<table>

<tr><td>Alt+1~9</td><td>Switch tabs</td></tr>

<tr><td>Ctrl+R</td><td>Scan serial ports</td></tr>

<tr><td>Ctrl+N</td><td>Add a serial port manually</td></tr>

<tr><td>Ctrl+F</td><td>Find</td></tr>

<tr><td>F3/Shift+F3</td><td>Find next/previous</td></tr>

</table>

<p style="color: gray; margin-top: 15px;">

© 2026 | Python + PyQt5<br>

Windows / Linux

</p>

"""

        QMessageBox.about(self, "About TermLink", about_text)

    def _show_changelog(self):

        """显示更新日志对话框"""

        from PyQt5.QtWidgets import QTextBrowser

        dialog = QDialog(self)

        dialog.setWindowTitle("Changelog - TermLink")

        dialog.setMinimumSize(600, 500)

        layout = QVBoxLayout(dialog)

        # 使用 QTextBrowser 显示 Markdown 风格的内容

        text_browser = QTextBrowser()

        text_browser.setOpenExternalLinks(True)

        text_browser.setStyleSheet("""

            QTextBrowser {

                background-color: #fafafa;

                border: 1px solid #ddd;

                padding: 10px;

                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;

                font-size: 13px;

            }

        """)

        changelog_html = """

<h2 style="color: #2c3e50;">v1.0.5 (2026-03-18)</h2>

<h3 style="color: #27ae60;">New</h3>

<ul>

<li><b>Python 3.13+ Telnet support</b>: Added SimpleTelnet to replace the removed telnetlib module.</li>

</ul>

<h3 style="color: #3498db;">Improvements</h3>

<ul>

<li><b>About dialog</b>: Redesigned the About dialog with HTML formatting.</li>

<li><b>Remote serial configuration</b>: Avoid saving dynamic remote serial sessions into local config.</li>

<li><b>Device information sync</b>: Send existing device information to newly connected clients.</li>

</ul>

<h3 style="color: #e74c3c;">Fixes</h3>

<ul>

<li>Fixed startup errors caused by saving remote serial sessions as local ports.</li>

<li>Fixed missing device information for newly connected clients.</li>

</ul>

<hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">

<h2 style="color: #2c3e50;">v1.0.3 (2026-01-08)</h2>

<h3 style="color: #27ae60;">New</h3>

<ul>

<li><b>Device information</b>: Read device version and IP address after connecting.</li>

<li><b>Terminal search</b>: Added up/down search, regular expressions, and live highlighting.</li>

<li><b>Terminal context menu</b>: Added copy, paste, find, break, clear, and log actions.</li>

<li><b>SysRq mode</b>: Wait for a SysRq command after sending Break.</li>

<li><b>Text selection</b>: Added drag selection, word selection, and copy-on-select.</li>

</ul>

<h3 style="color: #3498db;">Improvements</h3>

<ul>

<li>Optimized terminal rendering and reduced unnecessary repaints.</li>

<li>Improved scrollbar appearance in the dark theme.</li>

<li>Added buffer limits to reduce memory growth.</li>

<li>Reduced network locking deadlock risk.</li>

</ul>

<p style="color: #999; margin-top: 20px; font-size: 12px;">

See CHANGELOG.md in the project root for the full changelog.

</p>

"""

        text_browser.setHtml(changelog_html)

        layout.addWidget(text_browser)

        # 关闭按钮

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)

        buttons.accepted.connect(dialog.accept)

        layout.addWidget(buttons)

        dialog.exec_()

    def _setup_toolbar(self):

        """设置工具栏"""

        self.addToolBar(build_main_toolbar(self))

    def _setup_statusbar(self):

        """设置状态栏"""

        self.statusbar = QStatusBar()

        self.setStatusBar(self.statusbar)

        self.statusbar.showMessage("Ready")

        # 定时更新状态

        self._status_timer = QTimer()

        self._status_timer.timeout.connect(self._update_status)

        self._status_timer.start(1000)

        # 设置 Alt+数字 快捷键切换标签页

        self._setup_tab_shortcuts()

    def _show_highlight_rules(self, selected_text: str = ""):
        self._highlight_rules.show(selected_text)

    def _highlight_selection(self, selected_text: str = ""):
        self._highlight_rules.add_selection(selected_text)

    def _clear_highlight_rules(self):
        self._highlight_rules.clear()

    def _add_serial_port(self):

        """添加串口"""

        from .config_dialog import ConfigDialog

        dialog = ConfigDialog(parent=self)

        if dialog.exec_() == ConfigDialog.Accepted:

            port_config = dialog.get_config()

            self._create_session(port_config)

    def _add_ssh_connection(self):

        """添加 SSH 连接"""

        from .ssh_dialog import SSHConnectDialog

        dialog = SSHConnectDialog(self)

        # 预设为 SSH

        dialog.type_combo.setCurrentIndex(0)

        if dialog.exec_() == QDialog.Accepted:

            config = dialog.get_config()

            self._create_network_session(config)

    def _add_telnet_connection(self):

        """添加 Telnet 连接"""

        from .ssh_dialog import SSHConnectDialog

        dialog = SSHConnectDialog(self)

        # 预设为 Telnet

        dialog.type_combo.setCurrentIndex(1)

        if dialog.exec_() == QDialog.Accepted:

            config = dialog.get_config()

            self._create_network_session(config)

    def _add_remote_serial_connection(self):

        self._serial_access_controller.show_remote_connection()

    def _create_network_session(self, config):

        """创建 SSH/Telnet 会话"""

        if self._network_terminal_sessions is None:
            from .controllers.network_terminal_sessions import NetworkTerminalSessionController
            self._network_terminal_sessions = NetworkTerminalSessionController(self)

        self._network_terminal_sessions.create_session(config)

    def _scan_serial_ports(self) -> List[str]:

        """扫描所有可用串口（仅使用配置的扫描模式）"""

        ports = []

        # 仅使用配置的扫描模式

        if platform.system() == "Linux":

            for pattern in self.app_config.scan_patterns:

                ports.extend(glob.glob(pattern))

            # 过滤掉不存在或无权限的

            valid_ports = []

            for port in set(ports):

                try:

                    import os

                    if os.path.exists(port) and os.access(port, os.R_OK | os.W_OK):

                        valid_ports.append(port)

                except:

                    pass

            ports = valid_ports

        else:

            # Windows 使用 pyserial 列出串口

            ports = SerialWorker.list_ports()

        return sorted(set(ports))

    def _scan_and_connect_all(self):

        """扫描所有串口并让用户选择连接"""

        ports = self._scan_serial_ports()

        if not ports:

            QMessageBox.information(

                self, "Scan Results",

                f"No serial ports found.\n\nCurrent scan patterns:\n" + "\n".join(self.app_config.scan_patterns)

            )

            return

        port_labels = SerialWorker.list_port_labels() if platform.system() != "Linux" else {}
        from .dialogs import SerialPortPickerDialog

        dialog = SerialPortPickerDialog(
            ports,
            set(self._sessions.keys()),
            self,
            port_labels=port_labels,
            default_baudrate=self._default_baudrate,
        )

        if dialog.exec_() != QDialog.Accepted:

            return

        selected_ports = dialog.selected_ports()

        if not selected_ports:

            return

        serial_settings = dialog.serial_settings()
        self._default_baudrate = serial_settings["baudrate"]

        # 连接选中的串口

        new_count = 0

        for port in selected_ports:

            if port not in self._sessions:

                # 使用默认配置创建会话

                port_config = PortConfigData(

                    name=port.split("/")[-1] if "/" in port else port,

                    port=port,

                    baudrate=serial_settings["baudrate"],

                    data_bits=serial_settings["data_bits"],

                    parity=serial_settings["parity"],

                    stop_bits=serial_settings["stop_bits"],

                    flow_control=serial_settings["flow_control"],

                )

                self._create_session(port_config)

                new_count += 1

        self.statusbar.showMessage(f"Added {new_count} serial port(s). Connect manually.")

    def _create_session(self, port_config: PortConfigData):

        """创建串口会话"""

        self._local_serial_sessions.create_session(port_config)

    def _on_device_info_updated(self, tab: QWidget, port: str, version: str, ip: str):

        """设备信息更新处理"""

        # 更新本地 tooltip

        self._update_tab_tooltip(tab, version, ip)

        # 如果是服务端模式，广播给客户端

        if self._network_server and self._network_server.is_running:

            self._network_server.broadcast_device_info(port, version, ip)

    def _update_tab_tooltip(self, tab: QWidget, version: str, ip: str):

        """更新 tab 的 tooltip 显示设备信息"""

        index = self.tab_widget.indexOf(tab)

        if index >= 0:

            tab_name = self.tab_widget.tabText(index)

            # 构建 tooltip

            tooltip_parts = [tab_name]

            if ip:

                tooltip_parts.append(f"IP: {ip}")

            if version:

                tooltip_parts.append(f"\n{version}")

            tooltip = '\n'.join(tooltip_parts)

            self.tab_widget.setTabToolTip(index, tooltip)

    def _on_server_login_state_changed(self, port: str, state):

        """服务端模式：登录状态变化"""

        from core.login_state_machine import LoginState

        if state == LoginState.READY:

            # 登录成功，发送 ifconfig 获取 IP

            if port in self._sessions:

                worker, tab, config = self._sessions[port]

                # 标记正在等待 IP

                self._waiting_ip_ports = getattr(self, '_waiting_ip_ports', set())

                self._waiting_ip_ports.add(port)

                # 发送 ifconfig 命令

                worker.send_command("ifconfig eth0 | grep 'inet addr' || ifconfig eth0 | grep 'inet '")

    def _parse_ip_from_data(self, port: str, data: str):

        waiting_ports = getattr(self, "_waiting_ip_ports", set())

        if port not in waiting_ports:

            return

        ip = parse_ip_from_ifconfig(data)

        if ip:

            self._update_tab_name_with_ip(port, ip)

            waiting_ports.discard(port)

    def _update_tab_name_with_ip(self, port: str, ip: str):

        """更新标签页名称，添加 IP"""

        if port not in self._sessions:

            return

        worker, tab, config = self._sessions[port]

        # 获取串口简称

        port_name = port.split("/")[-1] if "/" in port else port

        new_name = f"{port_name} - {ip}"

        if hasattr(tab, "set_base_title"):

            tab.set_base_title(new_name)

        else:

            self._set_tab_title(tab, new_name)

        # 更新配置

        config.name = new_name

        # 通知客户端串口重命名

        if self._network_server:

            self._network_server.rename_port(port, new_name)

        self.statusbar.showMessage(f"Serial {port} IP: {ip}")

    def _close_tab(self, index: int):

        """关闭标签页"""

        tab = self.tab_widget.widget(index)

        # 找到对应的会话

        port_to_remove = None

        for port, (worker, t, _) in self._sessions.items():

            if t == tab:

                port_to_remove = port

                break

        if port_to_remove:

            if is_remote_session_key(port_to_remove):
                if self._remote_serial_sessions.close_session_by_key(port_to_remove):
                    self.statusbar.showMessage(f"Closed remote serial port: {port_to_remove}")
                return

            worker, tab, _ = self._sessions.pop(port_to_remove)

            if hasattr(tab, "terminal") and hasattr(tab.terminal, "close_watch_dialog"):
                tab.terminal.close_watch_dialog()

            tab.close_session()

            self.tab_widget.removeTab(index)

            # 更新服务端串口列表（通知客户端）

            self._update_server_port_list()

            self._refresh_connection_panel()

            self.statusbar.showMessage(f"Closed serial port: {port_to_remove}")

    def _connect_all(self):

        """连接所有串口"""

        self._session_controller.connect_all()

        self.statusbar.showMessage("Connecting all serial ports...")

    def _disconnect_all(self):

        """断开所有串口"""

        self._session_controller.disconnect_all()

        self.statusbar.showMessage("Disconnected all serial ports")

    def _current_session(self):

        tab = self.tab_widget.currentWidget()

        if not tab:

            return None

        for key, (worker, session_tab, config) in self._sessions.items():

            if session_tab == tab:

                return key, worker, session_tab, config

        return None

    def _run_command_set(self, command_set):

        session = self._current_session()

        if not session:

            QMessageBox.information(self, "Info", "Select a connected session first.")

            return

        _key, worker, tab, _config = session

        if not worker.is_connected:

            QMessageBox.information(self, "Info", "Connect the selected session first.")

            return

        for command in command_set.commands:

            worker.write(command + "\r")

        if hasattr(tab, "terminal"):

            tab.terminal.setFocus()

        self.statusbar.showMessage(
            f"Ran command set '{command_set.name}' ({len(command_set.commands)} command(s))"
        )

    def _save_config(self):

        """保存当前配置"""

        self._capture_user_preferences()

        # 更新配置（只保存本地串口，不保存远程串口）

        self.app_config.serial_ports = serial_port_configs_to_save(self._sessions)

        self.config_manager.save()

        self.statusbar.showMessage("Configuration saved")

    def _restore_user_preferences(self):

        """Restore saved window geometry and dock/toolbar layout."""

        geometry = getattr(self.app_config, "window_geometry", "")
        if geometry:
            self.restoreGeometry(QByteArray.fromHex(geometry.encode("ascii")))

        state = getattr(self.app_config, "window_state", "")
        if state:
            self.restoreState(QByteArray.fromHex(state.encode("ascii")))

        self.connection_panel.setVisible(
            getattr(self.app_config, "show_connections_panel", True)
        )
        self.runtime_log_panel.setVisible(
            getattr(self.app_config, "show_runtime_log_panel", False)
        )
        self.command_set_panel.setVisible(
            getattr(self.app_config, "show_command_sets_panel", False)
        )
        self._apply_dock_corner_policy()
        QTimer.singleShot(0, self._apply_dock_corner_policy)
        self.resizeDocks(
            [self.command_set_panel],
            [max(45, int(getattr(self.app_config, "command_sets_panel_width", 110)))],
            Qt.Horizontal,
        )

    def _capture_user_preferences(self):

        """Capture user-specific UI preferences for automatic persistence."""

        self.app_config.window_geometry = bytes(self.saveGeometry().toHex()).decode("ascii")
        self.app_config.window_state = bytes(self.saveState().toHex()).decode("ascii")
        self.app_config.show_connections_panel = self.connection_panel.isVisible()
        self.app_config.show_runtime_log_panel = self.runtime_log_panel.isVisible()
        self.app_config.show_command_sets_panel = self.command_set_panel.isVisible()
        self.app_config.command_sets_panel_width = max(45, self.command_set_panel.width())

    def _load_saved_ports(self):

        """加载已保存的串口配置"""

        for port_config in self.app_config.serial_ports:

            # 跳过远程串口配置（远程串口由网络客户端动态创建）

            if is_remote_session_key(port_config.port):

                continue

            self._create_session(port_config)

    def _update_status(self):

        """更新状态栏"""

        connected = sum(

            1 for _, (w, _, _) in self._sessions.items() if w.is_connected

        )

        total = len(self._sessions)

        status_parts = [f"Serial: {connected}/{total} connected"]

        # 网络状态

        if self._network_mode == SerialAccessMode.SERVER and self._network_server:

            clients = self._network_server.client_count

            status_parts.append(f"Remote server: {clients} client(s)")

        elif self._network_mode == SerialAccessMode.CLIENT and self._remote_clients.clients():

            if self._remote_clients.any_connected():

                status_parts.append("Remote client: connected")

            else:

                status_parts.append("Remote client: disconnected")

        self.statusbar.showMessage(" | ".join(status_parts))

    def _init_network(self):

        """初始化网络"""

        self._serial_access_controller.init_network()

    def _update_log_download_menu_visibility(self):

        """更新日志下载菜单的可见性"""

        self._serial_access_controller.update_log_download_menu_visibility()

    def _start_server(self):

        """启动服务端"""

        self._serial_access_controller.start_server()

    def _server_auto_scan_and_login(self):

        """服务端模式：自动扫描、连接并登录所有串口"""

        # 扫描串口

        ports = self._scan_serial_ports()

        if not ports:

            self.statusbar.showMessage("Remote server: no serial ports found")

            return

        # 连接所有扫描到的串口

        new_count = 0

        for port in ports:

            if port not in self._sessions:

                # 使用默认配置创建会话

                port_config = PortConfigData(

                    name=port.split("/")[-1] if "/" in port else port,

                    port=port,

                    baudrate=self._default_baudrate,

                )

                self._create_session(port_config)

                new_count += 1

        # 更新服务端串口列表（通知已连接的客户端）

        self._update_server_port_list()

        self.statusbar.showMessage(f"Remote server: added {new_count} serial port(s). Connect manually.")

    def _update_server_port_list(self):

        """更新服务端的串口列表"""

        self._serial_access_controller.update_server_port_list()

    def _start_client(self):

        """启动客户端 - 连接服务器，根据服务端串口自动创建标签页"""

        self._serial_access_controller.start_client()

    def _on_server_connected(self, server_id: str = ""):

        """连接到服务器成功"""

        self.statusbar.showMessage(f"Connected to {server_id or 'server'}. Waiting for serial port list...")

    def _on_server_disconnected(self, server_id: str = ""):

        """与服务器断开"""

        last_error = ""
        client = self._remote_clients.get(server_id) if server_id else self._network_client
        if client:
            last_error = getattr(client, "last_error", "")
        message = last_error or f"Disconnected from {server_id or 'server'}"
        self.statusbar.showMessage(message)

        if server_id:
            for key in list(self._sessions):
                if is_remote_session_key(key) and remote_session_server_id(key) == server_id:
                    self._remote_serial_sessions.close_session_by_key(
                        key,
                        refresh=False,
                        disconnect_if_empty=False,
                    )
            self._serial_access_controller.remove_client(server_id, disconnect=False)
        else:
            self._remote_serial_sessions.close_all()

        self._refresh_connection_panel()

    def _on_port_list_received(self, server_id_or_ports, ports: list = None):

        """收到服务端串口列表 - 为每个串口创建标签页"""

        if ports is None:
            server_id = ""
            ports = server_id_or_ports
        else:
            server_id = server_id_or_ports
        self._remote_serial_sessions.on_port_list_received(ports, server_id)

    def _on_remote_port_added(self, server_id_or_port: str, port: str = None):

        """服务端新增串口"""

        if port is None:
            server_id = ""
            port = server_id_or_port
        else:
            server_id = server_id_or_port
        self._remote_serial_sessions.on_port_added(port, server_id)

    def _on_remote_port_removed(self, server_id_or_port: str, port: str = None):

        """服务端移除串口"""

        if port is None:
            server_id = ""
            port = server_id_or_port
        else:
            server_id = server_id_or_port
        self._remote_serial_sessions.on_port_removed(port, server_id)

    def _on_remote_port_renamed(self, server_id_or_port: str, port_or_name: str, new_name: str = None):

        """服务端串口重命名（更新IP后）"""

        if new_name is None:
            server_id = ""
            port = server_id_or_port
            new_name = port_or_name
        else:
            server_id = server_id_or_port
            port = port_or_name
        self._remote_serial_sessions.on_port_renamed(port, new_name, server_id)

    def _on_remote_device_info(self, server_id_or_port: str, port_or_version: str, version_or_ip: str, ip: str = None):

        """收到远程串口的设备信息"""

        if ip is None:
            server_id = ""
            port = server_id_or_port
            version = port_or_version
            ip = version_or_ip
        else:
            server_id = server_id_or_port
            port = port_or_version
            version = version_or_ip
        self._remote_serial_sessions.on_device_info(port, version, ip, server_id)

    def _on_remote_data_received(self, server_id_or_port: str, port_or_data: str, data: str = None):

        """收到远程串口数据 - 转发到对应的标签页"""

        if data is None:
            server_id = ""
            port = server_id_or_port
            data = port_or_data
        else:
            server_id = server_id_or_port
            port = port_or_data
        self._remote_serial_sessions.on_data_received(port, data, server_id)

    def _create_remote_session(self, remote_port: str):

        """为远程串口创建会话"""

        self._remote_serial_sessions.create_session(remote_port)

    def _stop_network(self):

        """停止网络"""

        self._serial_access_controller.stop_network()

    def _on_client_connected(self, addr: str):

        """客户端连接（服务端模式）"""

        self.statusbar.showMessage(f"Client connected: {addr}")

        # 广播完整串口列表给新连接的客户端

        if self._network_server:

            self._network_server.broadcast_port_list()

        self._refresh_connection_panel()

    def _on_client_disconnected(self, addr: str):

        """客户端断开（服务端模式）"""

        self.statusbar.showMessage(f"Client disconnected: {addr}")

        self._refresh_connection_panel()

    def _on_client_updated(self, addr: str):

        """客户端状态更新（服务端模式）"""

        self._refresh_connection_panel()

    def _on_network_data_received(self, addr: str, port: str, data: str):

        """收到客户端数据（服务端模式）- 转发到指定串口"""

        # 将客户端发来的数据写入指定的本地串口

        if port and port in self._sessions:

            worker, tab, _ = self._sessions[port]

            if worker.is_connected:

                worker.write(data)

        else:

            # 没有指定串口，写入所有本地串口

            for p, (worker, tab, _) in self._sessions.items():

                if not is_remote_session_key(p) and worker.is_connected:

                    worker.write(data)

    def _on_break_requested(self, addr: str, port: str):

        """收到客户端 Break 请求（服务端模式）- 转发到指定串口"""

        if port and port in self._sessions:

            worker, tab, _ = self._sessions[port]

            if worker.is_connected and hasattr(worker, 'send_break'):

                worker.send_break()

    def _on_network_error(self, error: str):

        """网络错误"""

        self.statusbar.showMessage(f"Network error: {error}")
        current_client = self._network_client
        if current_client and (
            getattr(current_client, "last_error", "") == error
            or error.startswith(("Remote access denied", "Connection failed", "Cannot connect"))
        ):
            QMessageBox.warning(self, "Remote Access", error)

        self._refresh_connection_panel()

    def _broadcast_serial_data(self, port: str, data: str):

        """广播串口数据到网络（服务端模式）"""

        # 推送给共享串口客户端和自动化 API 订阅者

        if self._serial_access_server:

            self._serial_access_server.on_serial_data(port, data)

    def _on_worker_device_state_changed(self, port: str, old_state: str,

                                         new_state: str, detail: str):

        """设备状态变化，推送给串口访问服务订阅者"""

        if self._serial_access_server:

            self._serial_access_server.on_device_state_changed(port, old_state, new_state, detail)

    def _set_network_config(self):

        """设置网络配置"""

        self._serial_access_controller.show_settings()

    def _show_serial_remote_access_control(self):

        from .dialogs import SerialRemoteAccessControlDialog

        dialog = SerialRemoteAccessControlDialog(
            self._network_server,
            self.app_config,
            self.config_manager.save,
            self,
        )

        dialog.exec_()

        self._refresh_connection_panel()

    def closeEvent(self, event):

        """关闭窗口事件"""

        # 自动保存配置

        self._save_config()

        # 停止网络

        self._stop_network()

        runtime_log_panel = getattr(self, "runtime_log_panel", None)

        if runtime_log_panel:

            runtime_log_panel.dispose()

        # 关闭所有会话

        for port, (worker, tab, _) in self._sessions.items():

            tab.close_session()

        event.accept()


