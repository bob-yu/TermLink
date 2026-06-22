import importlib.util
from pathlib import Path
import unittest


_selector_path = Path(__file__).resolve().parents[1] / "ui" / "session_config_selector.py"
_spec = importlib.util.spec_from_file_location("session_config_selector_under_test", _selector_path)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
serial_port_configs_to_save = _module.serial_port_configs_to_save


class SessionConfigSelectorTest(unittest.TestCase):
    def test_only_local_serial_configs_are_saved(self):
        local_config = object()
        sessions = {
            "COM1": (object(), object(), local_config),
            "remote://COM2": (object(), object(), object()),
            "ssh://host:22": (object(), object(), None),
            "telnet://host:23": (object(), object(), None),
        }

        self.assertEqual(serial_port_configs_to_save(sessions), [local_config])


if __name__ == "__main__":
    unittest.main()
