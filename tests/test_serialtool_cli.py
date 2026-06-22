import unittest
from unittest.mock import patch
from io import StringIO

from automation import serialtool


class FakeClient:
    instances = []

    def __init__(self, host, port, password, timeout, source=""):
        self.host = host
        self.port = port
        self.password = password
        self.timeout = timeout
        self.source = source
        self.requests = []
        FakeClient.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _tb):
        pass

    def request(self, action, params=None):
        self.requests.append((action, params or {}))
        return {"code": 0, "message": "ok"}

    def send_and_watch(self, port, data, duration):
        self.requests.append(("send_and_watch", {"port": port, "data": data, "duration": duration}))
        return {"code": 0, "message": "ok", "data": {"events": []}}

    def watch(
        self,
        port,
        duration=2.0,
        expect=None,
        idle_timeout=None,
        start_seq=None,
        from_position="latest",
        regex=False,
    ):
        self.requests.append((
            "watch",
            {
                "port": port,
                "duration": duration,
                "expect": expect,
                "idle_timeout": idle_timeout,
                "start_seq": start_seq,
                "from": from_position,
                "regex": regex,
            },
        ))
        return {"code": 0, "message": "ok", "data": {"output": ""}}

    def buffer_state(self, port):
        self.requests.append(("buffer_state", {"port": port}))
        return {"code": 0, "message": "ok", "data": {"port": port}}


class FailingClient(FakeClient):
    def __enter__(self):
        raise ConnectionError("Remote access denied: IP is banned")


class SerialToolCliTest(unittest.TestCase):
    def setUp(self):
        FakeClient.instances = []

    @patch("sys.stdout", new_callable=StringIO)
    @patch("automation.serialtool.SerialAccessApiClient", FakeClient)
    def test_server_port_does_not_conflict_with_serial_port_argument(self, _stdout):
        rc = serialtool.main([
            "--host", "10.0.0.2",
            "--port", "56338",
            "send-command",
            "COM12",
            "ls",
        ])

        client = FakeClient.instances[0]
        self.assertEqual(rc, 0)
        self.assertEqual(client.port, 56338)
        self.assertEqual(client.source, "cli")
        self.assertEqual(
            client.requests,
            [(
                "command",
                {
                    "port": "COM12",
                    "command": "ls",
                    "expect": None,
                    "timeout": 30,
                    "idle_timeout": None,
                    "regex": False,
                },
            )],
        )

    @patch("sys.stdout", new_callable=StringIO)
    @patch("automation.serialtool.SerialAccessApiClient", FakeClient)
    def test_request_command_dispatches_arbitrary_action(self, _stdout):
        serialtool.main(["request", "fetch_device_ip", "--params", '{"port":"COM5"}'])

        self.assertEqual(FakeClient.instances[0].requests, [("fetch_device_ip", {"port": "COM5"})])

    @patch("sys.stdout", new_callable=StringIO)
    @patch("automation.serialtool.SerialAccessApiClient", FakeClient)
    def test_send_and_watch_cli(self, _stdout):
        serialtool.main(["send-and-watch", "COM5", "ls\n", "--watch-seconds", "0.1"])

        self.assertEqual(
            FakeClient.instances[0].requests,
            [("send_and_watch", {"port": "COM5", "data": "ls\n", "duration": 0.1})],
        )

    @patch("sys.stdout", new_callable=StringIO)
    @patch("automation.serialtool.SerialAccessApiClient", FakeClient)
    def test_watch_cli_supports_cursor_parameters(self, _stdout):
        serialtool.main([
            "watch",
            "COM5",
            "--duration",
            "0.2",
            "--expect",
            "#",
            "--idle-timeout",
            "0.05",
            "--start-seq",
            "10",
            "--from",
            "seq",
        ])

        self.assertEqual(
            FakeClient.instances[0].requests,
            [(
                "watch",
                {
                    "port": "COM5",
                    "duration": 0.2,
                    "expect": "#",
                    "idle_timeout": 0.05,
                    "start_seq": 10,
                    "from": "seq",
                    "regex": False,
                },
            )],
        )

    @patch("sys.stdout", new_callable=StringIO)
    @patch("automation.serialtool.SerialAccessApiClient", FakeClient)
    def test_buffer_state_cli(self, _stdout):
        serialtool.main(["buffer-state", "COM5"])

        self.assertEqual(FakeClient.instances[0].requests, [("buffer_state", {"port": "COM5"})])

    @patch("sys.stdout", new_callable=StringIO)
    @patch("automation.serialtool.SerialAccessApiClient", FailingClient)
    def test_connection_error_prints_json_response(self, stdout):
        rc = serialtool.main(["list"])

        self.assertEqual(rc, 1)
        self.assertIn("Remote access denied: IP is banned", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
