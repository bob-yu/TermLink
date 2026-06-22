def key_sequence(key: int, text: str, qt) -> str:
    key_map = {
        qt.Key_Return: "\r",
        qt.Key_Enter: "\r",
        qt.Key_Backspace: "\x7f",
        qt.Key_Delete: "\x1b[3~",
        qt.Key_Escape: "\x1b",
        qt.Key_Tab: "\t",
        qt.Key_Up: "\x1b[A",
        qt.Key_Down: "\x1b[B",
        qt.Key_Right: "\x1b[C",
        qt.Key_Left: "\x1b[D",
        qt.Key_Home: "\x1b[H",
        qt.Key_End: "\x1b[F",
        qt.Key_PageUp: "\x1b[5~",
        qt.Key_PageDown: "\x1b[6~",
        qt.Key_Insert: "\x1b[2~",
        qt.Key_F1: "\x1bOP",
        qt.Key_F2: "\x1bOQ",
        qt.Key_F3: "\x1bOR",
        qt.Key_F4: "\x1bOS",
        qt.Key_F5: "\x1b[15~",
        qt.Key_F6: "\x1b[17~",
        qt.Key_F7: "\x1b[18~",
        qt.Key_F8: "\x1b[19~",
        qt.Key_F9: "\x1b[20~",
        qt.Key_F10: "\x1b[21~",
        qt.Key_F11: "\x1b[23~",
        qt.Key_F12: "\x1b[24~",
    }
    return key_map.get(key, text or "")


def control_sequence(key: int, qt) -> str:
    control_map = {
        qt.Key_C: "\x03",
        qt.Key_D: "\x04",
        qt.Key_Z: "\x1a",
        qt.Key_L: "\x0c",
    }
    if key in control_map:
        return control_map[key]
    if qt.Key_A <= key <= qt.Key_Z:
        return chr(key - qt.Key_A + 1)
    return ""
