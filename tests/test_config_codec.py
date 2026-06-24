import unittest

from utils.config_codec import create_default_config, parse_config, serialize_config
from utils.config_schema import (
    CommandSetData,
    DEFAULT_REMOTE_SERIAL_PORT,
    AppConfigData,
    HighlightRuleData,
    LoginConfigData,
    PortConfigData,
)


class ConfigCodecTest(unittest.TestCase):
    def test_default_config_matches_runtime_defaults(self):
        config = create_default_config()

        self.assertEqual(config.log_dir, "logs")
        self.assertEqual(config.serial_access_mode, "disabled")
        self.assertEqual(config.serial_access_port, DEFAULT_REMOTE_SERIAL_PORT)
        self.assertEqual(config.scan_patterns, ["/dev/ttyUSB*", "/dev/ttyACM*"])
        self.assertEqual(config.terminal_font_family, "")
        self.assertEqual(config.terminal_font_size, 11)
        self.assertTrue(config.log_enabled)
        self.assertTrue(config.log_timestamp)
        self.assertTrue(config.show_connections_panel)
        self.assertFalse(config.show_runtime_log_panel)
        self.assertFalse(config.show_command_sets_panel)
        self.assertEqual(config.command_sets_panel_width, 140)
        self.assertEqual(config.serial_access_max_clients, 16)
        self.assertEqual(config.serial_access_client_password, "")
        self.assertEqual(config.serial_access_default_permission, "read-write")
        self.assertEqual(config.serial_access_banned_ips, [])
        self.assertEqual(config.highlight_rules, [])

    def test_parse_fills_missing_values(self):
        config = parse_config(
            {
                "serial_ports": [
                    {
                        "name": "board",
                        "port": "COM3",
                    }
                ]
            }
        )

        port = config.serial_ports[0]
        self.assertEqual(port.baudrate, 115200)
        self.assertEqual(port.data_bits, 8)
        self.assertEqual(port.parity, "N")
        self.assertEqual(port.stop_bits, 1.0)
        self.assertEqual(port.flow_control, "none")
        self.assertEqual(port.login.username, "root")
        self.assertEqual(port.login.shell_prompt, ["#", "$"])
        self.assertEqual(config.log_max_file_size_mb, 50)

    def test_serial_access_uses_network_port_only(self):
        config = parse_config({"serial_access_port": 56400, "serial_access_enabled": False})

        self.assertEqual(config.serial_access_port, 56400)
        self.assertFalse(config.serial_access_enabled)
        config.serial_access_password = "secret"
        config.serial_access_client_password = "client-secret"
        config.serial_access_default_permission = "read-only"
        config.serial_access_banned_ips = ["10.0.0.5"]
        serialized = serialize_config(config)
        self.assertIn("serial_access_enabled", serialized)
        self.assertEqual(serialized["serial_access_password"], "secret")
        self.assertEqual(serialized["serial_access_client_password"], "client-secret")
        self.assertEqual(serialized["serial_access_default_permission"], "read-only")
        self.assertEqual(serialized["serial_access_banned_ips"], ["10.0.0.5"])
        self.assertNotIn("serial_" + "service_port", serialized)

    def test_legacy_client_password_defaults_to_server_password(self):
        config = parse_config({"serial_access_password": "server-pw"})

        self.assertEqual(config.serial_access_password, "server-pw")
        self.assertEqual(config.serial_access_client_password, "server-pw")

    def test_serialize_roundtrip(self):
        original = AppConfigData(
            serial_ports=[
                PortConfigData(
                    name="dut",
                    port="COM5",
                    baudrate=921600,
                    data_bits=7,
                    parity="E",
                    stop_bits=2.0,
                    flow_control="rtscts",
                    login=LoginConfigData(
                        username="admin",
                        password="secret",
                        login_prompt="user:",
                        password_prompt="pass:",
                        shell_prompt=[">"],
                    ),
                    auto_commands=["uname -a"],
                    keywords={"error": ["ERR"]},
                )
            ],
            serial_access_mode="client",
            serial_access_server_address=f"192.168.1.20:{DEFAULT_REMOTE_SERIAL_PORT}",
            log_enabled=False,
            show_connections_panel=False,
            show_runtime_log_panel=True,
            show_command_sets_panel=True,
            command_sets_panel_width=96,
            command_sets=[
                CommandSetData(name="Device Info", commands=["uname -a", "ifconfig"]),
            ],
            highlight_rules=[
                HighlightRuleData(
                    name="Errors",
                    pattern="error|fail",
                    color="#ffd6d6",
                    case_sensitive=False,
                    regex=True,
                    enabled=True,
                ),
            ],
        )

        self.assertEqual(parse_config(serialize_config(original)), original)

    def test_parse_command_sets_drops_empty_entries(self):
        config = parse_config(
            {
                "command_sets": [
                    {"name": "Device Info", "commands": ["uname -a", "", " ifconfig "]},
                    {"name": "", "commands": ["reboot"]},
                    {"name": "Empty", "commands": []},
                ]
            }
        )

        self.assertEqual(
            config.command_sets,
            [CommandSetData(name="Device Info", commands=["uname -a", "ifconfig"])],
        )

    def test_parse_legacy_network_keys(self):
        config = parse_config(
            {
                "network_mode": "server",
                "network_host": "127.0.0.1",
                "network_port": 56401,
                "server_address": "10.0.0.2:56401",
            }
        )

        self.assertEqual(config.serial_access_mode, "server")
        self.assertEqual(config.serial_access_host, "127.0.0.1")
        self.assertEqual(config.serial_access_port, 56401)
        self.assertEqual(config.serial_access_server_address, "10.0.0.2:56401")
        self.assertNotIn("network_port", serialize_config(config))

    def test_legacy_network_properties_proxy_serial_access_fields(self):
        config = create_default_config()

        config.network_mode = "server"
        config.network_host = "127.0.0.1"
        config.network_port = 56402
        config.server_address = "10.0.0.3:56402"

        self.assertEqual(config.serial_access_mode, "server")
        self.assertEqual(config.serial_access_host, "127.0.0.1")
        self.assertEqual(config.serial_access_port, 56402)
        self.assertEqual(config.serial_access_server_address, "10.0.0.3:56402")


if __name__ == "__main__":
    unittest.main()
