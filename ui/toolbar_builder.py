from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import QMenu, QToolBar, QToolButton

from .icon_provider import icon


def build_main_toolbar(window) -> QToolBar:
    toolbar = QToolBar("Main Toolbar")
    toolbar.setMovable(False)
    toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)
    toolbar.setIconSize(QSize(24, 24))
    toolbar.setStyleSheet("""
        QToolBar {
            spacing: 4px;
            padding: 4px 6px;
            border: none;
            border-bottom: 1px solid #d8dee4;
            background: #f8fafc;
        }
        QToolBar::separator {
            width: 1px;
            background: #d8dee4;
            margin: 5px 6px;
        }
        QToolButton {
            border: 1px solid transparent;
            border-radius: 5px;
            padding: 5px;
            background: transparent;
        }
        QToolButton:hover {
            border-color: #cbd5e1;
            background: #eef2f7;
        }
        QToolButton:pressed {
            background: #e2e8f0;
        }
        QToolButton::menu-indicator {
            image: none;
            width: 0;
        }
    """)

    toolbar.addAction(window.actions.scan_ports)
    _add_connection_menu(window, toolbar)

    toolbar.addSeparator()
    toolbar.addAction(window.actions.connect_all)
    toolbar.addAction(window.actions.disconnect_all)

    toolbar.addSeparator()
    _add_settings_menu(window, toolbar)

    toolbar.addSeparator()
    toolbar.addAction(window.actions.open_docs)
    _add_more_menu(window, toolbar)

    return toolbar


def _add_connection_menu(window, toolbar: QToolBar):
    add_connection_menu = QMenu(window)
    add_connection_menu.addAction(window.actions.add_serial)
    add_connection_menu.addAction(window.actions.add_ssh)
    add_connection_menu.addAction(window.actions.add_telnet)
    add_connection_menu.addAction(window.actions.add_raw_tcp)
    add_connection_menu.addAction(window.actions.add_remote_serial)

    button = QToolButton(window)
    button.setIcon(icon("plug-plus"))
    button.setToolTip("Add Connection")
    button.setStatusTip("Add Connection")
    button.setPopupMode(QToolButton.InstantPopup)
    button.setMenu(add_connection_menu)
    button.setAutoRaise(True)
    toolbar.addWidget(button)


def _add_settings_menu(window, toolbar: QToolBar):
    settings_menu = QMenu(window)
    settings_menu.addAction(window.actions.access_settings)
    settings_menu.addAction(window.actions.access_control)
    settings_menu.addAction(window.actions.terminal_settings)

    button = QToolButton(window)
    button.setIcon(icon("settings"))
    button.setToolTip("Settings")
    button.setStatusTip("Settings")
    button.setPopupMode(QToolButton.InstantPopup)
    button.setMenu(settings_menu)
    button.setAutoRaise(True)
    toolbar.addWidget(button)


def _add_more_menu(window, toolbar: QToolBar):
    connection_panel_action = window.connection_panel.toggleViewAction()
    connection_panel_action.setIcon(icon("panel-left"))
    connection_panel_action.setToolTip("Show or hide Connections")
    connection_panel_action.setStatusTip("Show or hide Connections")

    runtime_log_action = window.runtime_log_panel.toggleViewAction()
    runtime_log_action.setIcon(icon("scroll-text"))
    runtime_log_action.setToolTip("Show or hide Runtime Log")
    runtime_log_action.setStatusTip("Show or hide Runtime Log")

    command_sets_action = window.command_set_panel.toggleViewAction()
    command_sets_action.setIcon(icon("terminal-gear"))
    command_sets_action.setToolTip("Show or hide Command Sets")
    command_sets_action.setStatusTip("Show or hide Command Sets")

    more_menu = QMenu(window)
    more_menu.addAction(connection_panel_action)
    more_menu.addAction(runtime_log_action)
    more_menu.addAction(command_sets_action)
    more_menu.addSeparator()
    more_menu.addAction(window.actions.download_logs)
    if window.actions.download_logs.isVisible():
        more_menu.addSeparator()
    more_menu.addAction(window.actions.about)
    more_menu.addSeparator()
    more_menu.addAction(window.actions.exit_app)

    button = QToolButton(window)
    button.setIcon(icon("ellipsis"))
    button.setToolTip("More actions")
    button.setStatusTip("More actions")
    button.setPopupMode(QToolButton.InstantPopup)
    button.setMenu(more_menu)
    button.setAutoRaise(True)
    toolbar.addWidget(button)
