import unittest

from automation.mcp_server import MinimalMcpServer


class FakeClient:
    def __init__(self):
        self.requests = []

    def request(self, action, params=None):
        self.requests.append((action, params or {}))
        return {"code": 0, "message": "ok", "data": {"action": action}}


class AutomationMcpServerTest(unittest.TestCase):
    def test_tools_list(self):
        server = MinimalMcpServer(FakeClient())

        response = server._handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})

        self.assertEqual(response["id"], 1)
        self.assertTrue(response["result"]["tools"])

    def test_tool_call_dispatches_to_serial_action(self):
        client = FakeClient()
        server = MinimalMcpServer(client)

        response = server._handle({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "serial_send_command",
                "arguments": {"port": "COM1", "command": "uname -a"},
            },
        })

        self.assertEqual(client.requests[0][0], "command")
        self.assertFalse(response["result"]["isError"])

    def test_watch_tool_uses_unified_watch_action(self):
        client = FakeClient()
        server = MinimalMcpServer(client)

        response = server._handle({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "serial_watch",
                "arguments": {
                    "port": "COM1",
                    "duration": 0.1,
                    "expect": "#",
                    "idle_timeout": 0.05,
                    "start_seq": 3,
                    "from": "seq",
                },
            },
        })

        self.assertEqual(
            client.requests[0],
            (
                "watch",
                {
                    "port": "COM1",
                    "duration": 0.1,
                    "expect": "#",
                    "idle_timeout": 0.05,
                    "start_seq": 3,
                    "from": "seq",
                    "regex": False,
                },
            ),
        )
        self.assertFalse(response["result"]["isError"])

    def test_buffer_state_tool_dispatches_to_serial_action(self):
        client = FakeClient()
        server = MinimalMcpServer(client)

        response = server._handle({
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "serial_buffer_state",
                "arguments": {"port": "COM1"},
            },
        })

        self.assertEqual(client.requests, [("buffer_state", {"port": "COM1"})])
        self.assertFalse(response["result"]["isError"])

    def test_legacy_send_command_tool_maps_to_unified_command(self):
        client = FakeClient()
        server = MinimalMcpServer(client)

        server._handle({
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "serial_send_command",
                "arguments": {"port": "COM1", "command": "ls", "duration": 0.1},
            },
        })

        self.assertEqual(
            client.requests,
            [(
                "command",
                {
                    "port": "COM1",
                    "command": "ls",
                    "expect": None,
                    "duration": 0.1,
                    "idle_timeout": 0.3,
                    "regex": False,
                },
            )],
        )


if __name__ == "__main__":
    unittest.main()
