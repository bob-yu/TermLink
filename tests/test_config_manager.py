import json
import os
import sys
import tempfile
import unittest
from unittest import mock

from utils.config_manager import ConfigManager
from utils.config_schema import PortConfigData


class ConfigManagerTest(unittest.TestCase):
    def test_load_creates_default_config_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.json")
            manager = ConfigManager(config_path)

            config = manager.load()

            self.assertEqual(config.log_dir, "logs")
            self.assertTrue(os.path.exists(config_path))

    def test_save_persists_current_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.json")
            manager = ConfigManager(config_path)
            manager.load()
            manager.add_port_config(PortConfigData(name="board", port="COM7"))
            manager.save()

            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.assertEqual(data["serial_ports"][0]["name"], "board")
            self.assertEqual(data["serial_ports"][0]["port"], "COM7")

    def test_missing_config_uses_template_when_available(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.json")
            template_path = os.path.join(temp_dir, "config.example.json")
            with open(template_path, "w", encoding="utf-8") as f:
                json.dump({"terminal_font_size": 14, "serial_access_port": 57000}, f)

            manager = ConfigManager(config_path)
            config = manager.load()

            self.assertEqual(config.terminal_font_size, 14)
            self.assertEqual(config.serial_access_port, 57000)
            self.assertTrue(os.path.exists(config_path))

    def test_frozen_runtime_uses_executable_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            exe_dir = os.path.join(temp_dir, "TermLink")
            resource_dir = os.path.join(exe_dir, "_internal")
            os.makedirs(resource_dir)
            exe_path = os.path.join(exe_dir, "TermLink.exe")
            template_path = os.path.join(resource_dir, "config.example.json")
            with open(template_path, "w", encoding="utf-8") as f:
                json.dump({"terminal_font_size": 13}, f)

            with mock.patch.object(sys, "frozen", True, create=True), mock.patch.object(
                sys, "executable", exe_path
            ), mock.patch.object(sys, "_MEIPASS", resource_dir, create=True):
                manager = ConfigManager()
                config = manager.load()

            self.assertEqual(config.terminal_font_size, 13)
            self.assertEqual(manager.config_file, os.path.join(exe_dir, "config.json"))
            self.assertTrue(os.path.exists(manager.config_file))


if __name__ == "__main__":
    unittest.main()
