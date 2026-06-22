import json
import os
import sys
from typing import Dict, Optional

from .config_codec import create_default_config, parse_config, serialize_config
from .config_schema import AppConfigData, PortConfigData


class ConfigManager:
    DEFAULT_CONFIG_FILE = "config.json"
    EXAMPLE_CONFIG_FILE = "config.example.json"
    APP_NAME = "TermLink"

    def __init__(self, config_file: str = None):
        self.config_file = config_file or self._get_config_path()
        self._config: Optional[AppConfigData] = None

    def _get_config_path(self) -> str:
        runtime_dir = self._get_runtime_dir()
        local_config = os.path.join(runtime_dir, self.DEFAULT_CONFIG_FILE)

        if os.path.exists(local_config):
            if os.access(local_config, os.W_OK):
                return local_config
        elif os.access(runtime_dir, os.W_OK):
            return local_config

        user_config_dir = self._get_user_config_dir()
        os.makedirs(user_config_dir, exist_ok=True)
        return os.path.join(user_config_dir, self.DEFAULT_CONFIG_FILE)

    def _get_runtime_dir(self) -> str:
        if getattr(sys, "frozen", False):
            return os.path.dirname(os.path.abspath(sys.executable))
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _get_resource_dir(self) -> str:
        if getattr(sys, "frozen", False):
            return getattr(sys, "_MEIPASS", self._get_runtime_dir())
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _get_user_config_dir(self) -> str:
        if os.name == "nt":
            base = os.environ.get("APPDATA", os.path.expanduser("~"))
        else:
            base = os.path.expanduser("~")
        return os.path.join(base, f".{self.APP_NAME}")

    def _get_log_dir(self) -> str:
        runtime_dir = self._get_runtime_dir()
        local_logs = os.path.join(runtime_dir, "logs")

        if os.access(runtime_dir, os.W_OK):
            os.makedirs(local_logs, exist_ok=True)
            return local_logs

        user_logs = os.path.join(self._get_user_config_dir(), "logs")
        os.makedirs(user_logs, exist_ok=True)
        return user_logs

    def load(self) -> AppConfigData:
        if not os.path.exists(self.config_file):
            self._config = self._create_default_config()
            self._try_save()
            return self._config

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._config = parse_config(data)
        except Exception as exc:
            print(f"Error loading config: {exc}")
            self._config = self._create_default_config()

        if not os.access(self._config.log_dir, os.W_OK):
            self._config.log_dir = self._get_log_dir()

        return self._config

    def save(self):
        self._try_save()

    def _try_save(self):
        if not self._config:
            return

        data = serialize_config(self._config)

        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except PermissionError:
            self.config_file = os.path.join(
                self._get_user_config_dir(),
                self.DEFAULT_CONFIG_FILE,
            )
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            print(f"Config saved to: {self.config_file}")

    def get_config(self) -> AppConfigData:
        if not self._config:
            self.load()
        return self._config

    def _create_default_config(self) -> AppConfigData:
        example_path = self._get_example_config_path()
        if example_path and os.path.exists(example_path):
            try:
                with open(example_path, "r", encoding="utf-8") as f:
                    return parse_config(json.load(f))
            except Exception as exc:
                print(f"Error loading config template: {exc}")
        return create_default_config()

    def _get_example_config_path(self) -> Optional[str]:
        runtime_dir = self._get_runtime_dir()
        resource_dir = self._get_resource_dir()
        candidates = [
            os.path.join(os.path.dirname(self.config_file), self.EXAMPLE_CONFIG_FILE),
            os.path.join(runtime_dir, self.EXAMPLE_CONFIG_FILE),
            os.path.join(resource_dir, self.EXAMPLE_CONFIG_FILE),
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return None

    def _parse_config(self, data: Dict) -> AppConfigData:
        return parse_config(data)

    def _serialize_config(self, config: AppConfigData) -> Dict:
        return serialize_config(config)

    def add_port_config(self, port_config: PortConfigData):
        if not self._config:
            self.load()
        self._config.serial_ports.append(port_config)

    def remove_port_config(self, port: str):
        if not self._config:
            return
        self._config.serial_ports = [
            item for item in self._config.serial_ports if item.port != port
        ]

