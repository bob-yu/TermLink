import unittest

from core.serial_access_api_router import SerialAccessApiRouter
from core.serial_access_protocol import ERR_BAD_PARAMS, ERR_INTERNAL, ERR_OK


class FakeService:
    def __init__(self):
        self.calls = []

    def list_ports(self):
        return {"code": ERR_OK, "ports": ["COM1"]}

    def write(self, port, data):
        self.calls.append(("write", port, data))
        return {"code": ERR_OK}

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
        self.calls.append(("watch", port, duration, expect, idle_timeout, start_seq, from_position, regex))
        return {
            "code": ERR_OK,
            "data": {
                "output": "hello\nworld",
                "reason": "idle_timeout",
                "matched": False,
            },
        }

    def buffer_state(self, port):
        self.calls.append(("buffer_state", port))
        return {
            "code": ERR_OK,
            "data": {
                "port": port,
                "current_bytes": 1,
                "max_bytes": 10,
                "oldest_seq": 1,
                "latest_seq": 2,
                "dropped_bytes": 0,
                "dropped_chunks": 0,
                "last_drop_time": 0,
            },
        }

    def send_command(
        self,
        port,
        command,
        expect=None,
        timeout=30,
        duration=None,
        idle_timeout=None,
        regex=False,
    ):
        self.calls.append(("command", port, command, expect, timeout, duration, idle_timeout, regex))
        return {
            "code": ERR_OK,
            "data": {
                "output": f"{command}\nresult",
                "reason": "idle_timeout",
                "matched": False,
            },
        }


class SerialAccessApiRouterTest(unittest.TestCase):
    def test_reports_missing_service(self):
        router = SerialAccessApiRouter(None, lambda _addr, _port: None, lambda _addr, _port: None)

        result = router.dispatch("client", "list_ports", {})

        self.assertEqual(result["code"], ERR_INTERNAL)

    def test_dispatches_service_action(self):
        service = FakeService()
        router = SerialAccessApiRouter(service, lambda _addr, _port: None, lambda _addr, _port: None)

        result = router.dispatch("client", "write_data", {"port": "COM1", "data": "abc"})

        self.assertEqual(result["code"], ERR_OK)
        self.assertEqual(service.calls, [("write", "COM1", "abc")])

    def test_logs_api_request_and_response(self):
        service = FakeService()
        router = SerialAccessApiRouter(service, lambda _addr, _port: None, lambda _addr, _port: None)

        with self.assertLogs("core.serial_access_api_router", level="INFO") as captured:
            result = router.dispatch(
                "127.0.0.1:50000",
                "write_data",
                {"port": "COM1", "data": "abc", "source": "cli"},
            )

        self.assertEqual(result["code"], ERR_OK)
        self.assertIn(
            "Serial API request from 127.0.0.1:50000: source=cli action=write_data port=COM1",
            captured.output[0],
        )
        self.assertIn("Serial API write request: source=cli port=COM1 data=abc", captured.output[1])
        self.assertIn(
            "Serial API response to 127.0.0.1:50000: source=cli action=write_data code=0",
            captured.output[2],
        )

    def test_logs_command_output_summary(self):
        service = FakeService()
        router = SerialAccessApiRouter(service, lambda _addr, _port: None, lambda _addr, _port: None)

        with self.assertLogs("core.serial_access_api_router", level="INFO") as captured:
            result = router.dispatch(
                "127.0.0.1:50000",
                "command",
                {"port": "COM1", "command": "pwd", "source": "mcp"},
            )

        self.assertEqual(result["code"], ERR_OK)
        joined = "\n".join(captured.output)
        self.assertIn("Serial API command request: source=mcp port=COM1 command=pwd", joined)
        self.assertIn("Serial API output response: source=mcp action=command port=COM1", joined)
        self.assertIn("preview=pwd\\nresult", joined)

    def test_dispatches_unified_watch_action(self):
        service = FakeService()
        router = SerialAccessApiRouter(service, lambda _addr, _port: None, lambda _addr, _port: None)

        result = router.dispatch(
            "client",
            "watch",
            {"port": "COM1", "duration": 1.5, "expect": "#", "idle_timeout": 0.2, "regex": True},
        )

        self.assertEqual(result["code"], ERR_OK)
        self.assertEqual(service.calls, [("watch", "COM1", 1.5, "#", 0.2, None, "latest", True)])

    def test_dispatches_watch_from_oldest(self):
        service = FakeService()
        router = SerialAccessApiRouter(service, lambda _addr, _port: None, lambda _addr, _port: None)

        result = router.dispatch("client", "watch", {"port": "COM1", "from": "oldest"})

        self.assertEqual(result["code"], ERR_OK)
        self.assertEqual(service.calls, [("watch", "COM1", 2.0, None, None, None, "oldest", False)])

    def test_dispatches_buffer_state(self):
        service = FakeService()
        router = SerialAccessApiRouter(service, lambda _addr, _port: None, lambda _addr, _port: None)

        result = router.dispatch("client", "buffer_state", {"port": "COM1"})

        self.assertEqual(result["code"], ERR_OK)
        self.assertEqual(service.calls, [("buffer_state", "COM1")])

    def test_dispatches_unified_command_action(self):
        service = FakeService()
        router = SerialAccessApiRouter(service, lambda _addr, _port: None, lambda _addr, _port: None)

        result = router.dispatch(
            "client",
            "command",
            {"port": "COM1", "command": "ls", "duration": 2.0, "idle_timeout": 0.3},
        )

        self.assertEqual(result["code"], ERR_OK)
        self.assertEqual(service.calls, [("command", "COM1", "ls", None, 30, 2.0, 0.3, False)])

    def test_subscribe_validates_port(self):
        subscribed = []
        router = SerialAccessApiRouter(
            FakeService(),
            lambda addr, port: subscribed.append((addr, port)),
            lambda _addr, _port: None,
        )

        missing = router.dispatch("client", "subscribe", {})
        ok = router.dispatch("client", "subscribe", {"port": "COM1"})

        self.assertEqual(missing["code"], ERR_BAD_PARAMS)
        self.assertEqual(ok["code"], ERR_OK)
        self.assertEqual(subscribed, [("client", "COM1")])

    def test_unknown_action(self):
        router = SerialAccessApiRouter(FakeService(), lambda _addr, _port: None, lambda _addr, _port: None)

        result = router.dispatch("client", "missing", {})

        self.assertEqual(result["code"], ERR_BAD_PARAMS)


if __name__ == "__main__":
    unittest.main()
