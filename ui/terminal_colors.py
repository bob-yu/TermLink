from PyQt5.QtGui import QColor


BG_COLOR = QColor(30, 30, 30)
FG_COLOR = QColor(212, 212, 212)


NAMED_COLORS = {
    "black": QColor(0, 0, 0),
    "red": QColor(205, 49, 49),
    "green": QColor(13, 188, 121),
    "brown": QColor(229, 229, 16),
    "yellow": QColor(229, 229, 16),
    "blue": QColor(36, 114, 200),
    "magenta": QColor(188, 63, 188),
    "cyan": QColor(17, 168, 205),
    "white": QColor(229, 229, 229),
    "default": FG_COLOR,
    "brightblack": QColor(102, 102, 102),
    "brightred": QColor(241, 76, 76),
    "brightgreen": QColor(35, 209, 139),
    "brightyellow": QColor(245, 245, 67),
    "brightblue": QColor(59, 142, 234),
    "brightmagenta": QColor(214, 112, 214),
    "brightcyan": QColor(41, 184, 219),
    "brightwhite": QColor(255, 255, 255),
}

ANSI_ALIASES = {
    "ansiblack": "black",
    "ansired": "red",
    "ansigreen": "green",
    "ansiyellow": "yellow",
    "ansiblue": "blue",
    "ansimagenta": "magenta",
    "ansicyan": "cyan",
    "ansiwhite": "white",
    "ansibrightblack": "brightblack",
    "ansibrightred": "brightred",
    "ansibrightgreen": "brightgreen",
    "ansibrightyellow": "brightyellow",
    "ansibrightblue": "brightblue",
    "ansibrightmagenta": "brightmagenta",
    "ansibrightcyan": "brightcyan",
    "ansibrightwhite": "brightwhite",
}


def terminal_color(value, default: QColor) -> QColor:
    """Resolve pyte color values to QColor.

    pyte returns named colors for 16-color SGR values and six-digit RGB hex
    strings for 256-color / true-color SGR values.
    """
    if not value:
        return default
    if isinstance(value, QColor):
        return value

    name = str(value).strip().lower()
    if name in ANSI_ALIASES:
        name = ANSI_ALIASES[name]
    if name == "default":
        return default
    if default == BG_COLOR and name in ("black", "ansiblack"):
        return default
    if name in NAMED_COLORS:
        return NAMED_COLORS[name]
    if len(name) == 6:
        try:
            return QColor(int(name[0:2], 16), int(name[2:4], 16), int(name[4:6], 16))
        except ValueError:
            return default
    if name.startswith("#") and len(name) == 7:
        color = QColor(name)
        if color.isValid():
            return color
    return default
