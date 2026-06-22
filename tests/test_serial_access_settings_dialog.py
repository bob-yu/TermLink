import importlib.util
from pathlib import Path
import sys
import types
import unittest


if "PyQt5" not in sys.modules:
    sys.modules["PyQt5"] = types.ModuleType("PyQt5")
if "PyQt5.QtWidgets" not in sys.modules:
    qtwidgets = types.ModuleType("PyQt5.QtWidgets")
    sys.modules["PyQt5.QtWidgets"] = qtwidgets
for name in [
    "QCheckBox",
    "QDialog",
    "QDialogButtonBox",
    "QFormLayout",
    "QGroupBox",
    "QLineEdit",
    "QComboBox",
    "QSpinBox",
    "QVBoxLayout",
]:
    setattr(sys.modules["PyQt5.QtWidgets"], name, type(name, (), {}))

_dialog_path = Path(__file__).resolve().parents[1] / "ui" / "dialogs" / "serial_access_settings_dialog.py"
_spec = importlib.util.spec_from_file_location("serial_access_settings_dialog_under_test", _dialog_path)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
SerialAccessSettings = _module.SerialAccessSettings


class SerialAccessSettingsTest(unittest.TestCase):
    def test_settings_value_object(self):
        settings = SerialAccessSettings(
            host="0.0.0.0",
            port=56337,
            access_enabled=True,
            access_password="secret",
            max_clients=16,
            default_permission="read-only",
        )

        self.assertEqual(settings.host, "0.0.0.0")
        self.assertEqual(settings.port, 56337)
        self.assertEqual(settings.access_password, "secret")
        self.assertEqual(settings.max_clients, 16)
        self.assertEqual(settings.default_permission, "read-only")


if __name__ == "__main__":
    unittest.main()
