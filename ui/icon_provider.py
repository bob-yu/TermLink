from pathlib import Path

from PyQt5.QtGui import QIcon


ICON_DIR = Path(__file__).resolve().parent / "resources" / "icons"


def icon(name: str) -> QIcon:
    path = ICON_DIR / f"{name}.svg"
    if not path.exists():
        return QIcon()
    return QIcon(str(path))
