from PyQt5.QtWidgets import QAction, QMenu


MENU_STYLE = """
    QMenu {
        background-color: #ffffff;
        border: 1px solid #cccccc;
        padding: 4px;
    }
    QMenu::item {
        padding: 6px 24px;
        color: #333333;
    }
    QMenu::item:selected {
        background-color: #0078d4;
        color: #ffffff;
    }
    QMenu::separator {
        height: 1px;
        background-color: #e0e0e0;
        margin: 4px 8px;
    }
"""


def build_terminal_context_menu(view) -> QMenu:
    menu = QMenu(view)
    menu.setStyleSheet(MENU_STYLE)

    copy_action = QAction("Copy", view)
    copy_action.setShortcut("Ctrl+Shift+C")
    copy_action.triggered.connect(view._copy_selection)
    copy_action.setEnabled(view._has_selection)
    menu.addAction(copy_action)

    paste_action = QAction("Paste", view)
    paste_action.setShortcut("Ctrl+Shift+V")
    paste_action.triggered.connect(view._paste_clipboard)
    menu.addAction(paste_action)

    select_all_action = QAction("Select All", view)
    select_all_action.triggered.connect(view._select_all)
    menu.addAction(select_all_action)

    menu.addSeparator()

    find_action = QAction("Find...", view)
    find_action.setShortcut("Ctrl+F")
    find_action.triggered.connect(view._show_search_dialog)
    menu.addAction(find_action)

    watch_action = QAction("Watch...", view)
    watch_action.triggered.connect(view._show_watch_dialog)
    menu.addAction(watch_action)

    highlight_selection_action = QAction("Highlight Selection", view)
    highlight_selection_action.triggered.connect(view._highlight_selection)
    highlight_selection_action.setEnabled(view._has_selection)
    menu.addAction(highlight_selection_action)

    highlight_settings_action = QAction("Highlight Settings...", view)
    highlight_settings_action.triggered.connect(view._show_highlight_rules)
    menu.addAction(highlight_settings_action)

    clear_highlights_action = QAction("Clear Highlights", view)
    clear_highlights_action.triggered.connect(view._clear_highlight_rules)
    menu.addAction(clear_highlights_action)

    scroll_bottom_action = QAction("Scroll to Bottom", view)
    scroll_bottom_action.setShortcut("Ctrl+End")
    scroll_bottom_action.triggered.connect(view.scroll_to_bottom)
    menu.addAction(scroll_bottom_action)

    menu.addSeparator()

    connect_action = QAction("Connect", view)
    connect_action.triggered.connect(view._connect_session)
    connect_action.setEnabled(not view._is_session_connected())
    menu.addAction(connect_action)

    disconnect_action = QAction("Disconnect", view)
    disconnect_action.triggered.connect(view._disconnect_session)
    disconnect_action.setEnabled(view._is_session_connected())
    menu.addAction(disconnect_action)

    break_action = QAction("Send Break", view)
    break_action.triggered.connect(view._send_break)
    menu.addAction(break_action)

    menu.addSeparator()

    clear_menu = menu.addMenu("Clear")

    clear_screen_action = QAction("Clear Screen", view)
    clear_screen_action.triggered.connect(view._clear_current_screen)
    clear_menu.addAction(clear_screen_action)

    clear_scrollback_action = QAction("Clear Scrollback", view)
    clear_scrollback_action.triggered.connect(view._clear_scrollback)
    clear_menu.addAction(clear_scrollback_action)

    clear_all_action = QAction("Clear All", view)
    clear_all_action.triggered.connect(view.clear)
    clear_menu.addAction(clear_all_action)

    menu.addSeparator()

    log_menu = menu.addMenu("Log")
    if getattr(view, "_log_enabled", True):
        stop_log_action = QAction("Stop Logging", view)
        stop_log_action.triggered.connect(lambda: view._toggle_log(False))
        log_menu.addAction(stop_log_action)
    else:
        start_log_action = QAction("Start Logging...", view)
        start_log_action.triggered.connect(lambda: view._toggle_log(True))
        log_menu.addAction(start_log_action)

    log_menu.addSeparator()

    open_log_file_action = QAction("Open Log File", view)
    open_log_file_action.triggered.connect(view._open_log_file)
    log_menu.addAction(open_log_file_action)

    open_log_folder_action = QAction("Open Log Folder", view)
    open_log_folder_action.triggered.connect(view._open_log_folder)
    log_menu.addAction(open_log_folder_action)

    menu.addSeparator()

    font_action = QAction("Terminal Settings...", view)
    font_action.triggered.connect(view._show_terminal_settings)
    menu.addAction(font_action)

    return menu
