import unittest

from core.network_address import NetworkAddress, parse_server_address
from utils.config_schema import DEFAULT_REMOTE_SERIAL_PORT


class NetworkAddressTest(unittest.TestCase):
    def test_uses_default_port_without_explicit_port(self):
        self.assertEqual(
            parse_server_address("10.3.22.17", DEFAULT_REMOTE_SERIAL_PORT),
            NetworkAddress("10.3.22.17", DEFAULT_REMOTE_SERIAL_PORT),
        )

    def test_uses_explicit_port(self):
        self.assertEqual(
            parse_server_address("10.3.22.17:56400", DEFAULT_REMOTE_SERIAL_PORT),
            NetworkAddress("10.3.22.17", 56400),
        )

    def test_zero_address_connects_to_loopback(self):
        self.assertEqual(
            parse_server_address("0.0.0.0", DEFAULT_REMOTE_SERIAL_PORT),
            NetworkAddress("127.0.0.1", DEFAULT_REMOTE_SERIAL_PORT),
        )
        self.assertEqual(
            parse_server_address("0.0.0.0:56400", DEFAULT_REMOTE_SERIAL_PORT),
            NetworkAddress("127.0.0.1", 56400),
        )


if __name__ == "__main__":
    unittest.main()
