import importlib.util
import logging
from pathlib import Path
import sys
import types
import unittest


if "PyQt5" not in sys.modules:
    sys.modules["PyQt5"] = types.ModuleType("PyQt5")
if "PyQt5.QtCore" not in sys.modules:
    qtcore = types.ModuleType("PyQt5.QtCore")
    sys.modules["PyQt5.QtCore"] = qtcore
sys.modules["PyQt5.QtCore"].QObject = object
sys.modules["PyQt5.QtCore"].Qt = type("Qt", (), {
    "BottomDockWidgetArea": 1,
    "TopDockWidgetArea": 2,
    "RightDockWidgetArea": 4,
    "CustomContextMenu": 8,
})
sys.modules["PyQt5.QtCore"].pyqtSignal = lambda *args, **kwargs: None
if "PyQt5.QtWidgets" not in sys.modules:
    qtwidgets = types.ModuleType("PyQt5.QtWidgets")
    sys.modules["PyQt5.QtWidgets"] = qtwidgets
for name in [
    "QDockWidget",
    "QMenu",
    "QPlainTextEdit",
    "QVBoxLayout",
    "QWidget",
]:
    setattr(sys.modules["PyQt5.QtWidgets"], name, type(name, (), {}))

_panel_path = Path(__file__).resolve().parents[1] / "ui" / "widgets" / "runtime_log_panel.py"
_spec = importlib.util.spec_from_file_location("runtime_log_panel_under_test", _panel_path)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
RuntimeLogPanel = _module.RuntimeLogPanel


class RuntimeLogPanelTest(unittest.TestCase):
    def test_parse_level(self):
        self.assertEqual(RuntimeLogPanel._parse_level("12:00:00 ERROR [x] bad"), logging.ERROR)
        self.assertEqual(RuntimeLogPanel._parse_level("12:00:00 WARNING [x] warn"), logging.WARNING)
        self.assertEqual(RuntimeLogPanel._parse_level("12:00:00 DEBUG [x] debug"), logging.DEBUG)
        self.assertEqual(RuntimeLogPanel._parse_level("12:00:00 INFO [x] ok"), logging.INFO)


if __name__ == "__main__":
    unittest.main()
