from pathlib import Path
import sys

from PyQt5.QtGui import QIcon


ICON_DIR = Path(__file__).resolve().parent / "resources" / "icons"
APP_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))


def icon(name: str) -> QIcon:
    if name == "app":
        for path in (
            APP_ROOT / "app-icon.ico",
            Path(__file__).resolve().parents[1] / "assets" / "app-icon.ico",
        ):
            if path.exists():
                return QIcon(str(path))
    path = ICON_DIR / f"{name}.svg"
    if not path.exists():
        return QIcon()
    return QIcon(str(path))
