#!/usr/bin/env python3
"""Application entry point."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from ui.icon_provider import icon
from ui.main_window import MainWindow


def _set_windows_app_id():
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "TermLink.TermLink.1.0.5"
        )
    except Exception:
        pass


def main():
    _set_windows_app_id()

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("TermLink")
    app.setOrganizationName("TermLink")
    app.setStyle("Fusion")
    app.setWindowIcon(icon("app"))

    window = MainWindow()
    window.setWindowIcon(icon("app"))
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

