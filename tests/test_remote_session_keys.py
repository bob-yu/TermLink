import unittest

from core.remote_session_keys import (
    is_remote_session_key,
    make_remote_session_key,
    parse_remote_session_key,
    remote_session_port,
    remote_session_server_id,
    remote_tab_name,
)


class RemoteSessionKeysTest(unittest.TestCase):
    def test_remote_key_helpers(self):
        self.assertEqual(make_remote_session_key("COM1"), "remote://COM1")
        self.assertTrue(is_remote_session_key("remote://COM1"))
        self.assertFalse(is_remote_session_key("COM1"))
        self.assertEqual(
            make_remote_session_key("COM1", "127.0.0.1:56337"),
            "remote://127.0.0.1:56337/COM1",
        )
        self.assertEqual(
            parse_remote_session_key("remote://127.0.0.1:56337/COM1"),
            ("127.0.0.1:56337", "COM1"),
        )
        self.assertEqual(remote_session_server_id("remote://127.0.0.1:56337/COM1"), "127.0.0.1:56337")
        self.assertEqual(remote_session_port("remote://127.0.0.1:56337/COM1"), "COM1")

    def test_remote_tab_name_uses_basename(self):
        self.assertEqual(remote_tab_name("/dev/ttyUSB0"), "Remote:ttyUSB0")
        self.assertEqual(remote_tab_name("COM1"), "Remote:COM1")


if __name__ == "__main__":
    unittest.main()
