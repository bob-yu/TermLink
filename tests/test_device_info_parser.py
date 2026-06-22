import unittest

from core.device_info_parser import (
    parse_ip_from_ifconfig,
    parse_version_from_command_output,
)


class DeviceInfoParserTest(unittest.TestCase):
    def test_parses_legacy_ifconfig_format(self):
        self.assertEqual(
            parse_ip_from_ifconfig("inet addr:10.3.34.49  Bcast:10.3.34.255"),
            "10.3.34.49",
        )

    def test_parses_modern_ifconfig_format(self):
        self.assertEqual(
            parse_ip_from_ifconfig("inet 192.168.1.20  netmask 255.255.255.0"),
            "192.168.1.20",
        )

    def test_ignores_loopback_address(self):
        self.assertEqual(parse_ip_from_ifconfig("inet 127.0.0.1"), "")

    def test_returns_empty_string_without_address(self):
        self.assertEqual(parse_ip_from_ifconfig("no address here"), "")

    def test_parses_version_command_output(self):
        output = "cat /system/bin/version\nVersion 1.2.3\nBuild 456\n[root@device]#"

        self.assertEqual(
            parse_version_from_command_output(output),
            "Version 1.2.3 Build 456",
        )

    def test_returns_empty_string_without_version_prompt(self):
        self.assertEqual(parse_version_from_command_output("no prompt yet"), "")


if __name__ == "__main__":
    unittest.main()
