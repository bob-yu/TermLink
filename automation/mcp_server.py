import argparse
import json
import sys

from .serial_access_client import SerialAccessApiClient


TOOL_SCHEMAS = [
    {
        "name": "serial_list",
        "description": "List local serial ports exposed by TermLink.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "serial_state",
        "description": "Get state for one serial port.",
        "inputSchema": {
            "type": "object",
            "properties": {"port": {"type": "string"}},
            "required": ["port"],
        },
    },
    {
        "name": "serial_find_ip",
        "description": "Find a serial port by device IP.",
        "inputSchema": {
            "type": "object",
            "properties": {"device_ip": {"type": "string"}},
            "required": ["device_ip"],
        },
    },
    {
        "name": "serial_write",
        "description": "Write raw data to a serial port.",
        "inputSchema": {
            "type": "object",
            "properties": {"port": {"type": "string"}, "data": {"type": "string"}},
            "required": ["port", "data"],
        },
    },
    {
        "name": "serial_watch",
        "description": "Collect serial output until duration, expect, or idle timeout is reached.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "port": {"type": "string"},
                "duration": {"type": "number"},
                "expect": {"type": ["string", "null"]},
                "idle_timeout": {"type": ["number", "null"]},
                "start_seq": {"type": ["integer", "null"]},
                "from": {"type": "string", "enum": ["latest", "oldest", "seq"]},
                "regex": {"type": "boolean"},
            },
            "required": ["port"],
        },
    },
    {
        "name": "serial_buffer_state",
        "description": "Read ring-buffer state for one serial port, including oldest/latest seq and dropped data counters.",
        "inputSchema": {
            "type": "object",
            "properties": {"port": {"type": "string"}},
            "required": ["port"],
        },
    },
    {
        "name": "serial_command",
        "description": "Send a command and collect output until duration, expect, or idle timeout is reached.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "port": {"type": "string"},
                "command": {"type": "string"},
                "duration": {"type": "number"},
                "expect": {"type": ["string", "null"]},
                "idle_timeout": {"type": ["number", "null"]},
                "regex": {"type": "boolean"},
            },
            "required": ["port", "command"],
        },
    },
    {
        "name": "serial_break",
        "description": "Send a serial break signal.",
        "inputSchema": {
            "type": "object",
            "properties": {"port": {"type": "string"}},
            "required": ["port"],
        },
    },
    {
        "name": "serial_log",
        "description": "Read recent serial log lines.",
        "inputSchema": {
            "type": "object",
            "properties": {"port": {"type": "string"}, "lines": {"type": "integer"}},
            "required": ["port"],
        },
    },
    {
        "name": "serial_fetch_device_ip",
        "description": "Ask a device for network info and return the detected IP if available.",
        "inputSchema": {
            "type": "object",
            "properties": {"port": {"type": "string"}, "timeout": {"type": "integer"}},
            "required": ["port"],
        },
    },
]


ACTION_BY_TOOL = {
    "serial_list": ("list", lambda a: {}),
    "serial_list_ports": ("list", lambda a: {}),
    "serial_state": ("state", lambda a: {"port": a["port"]}),
    "serial_get_port_state": ("state", lambda a: {"port": a["port"]}),
    "serial_find_ip": ("find_ip", lambda a: {"device_ip": a["device_ip"]}),
    "serial_find_port_by_ip": ("find_ip", lambda a: {"device_ip": a["device_ip"]}),
    "serial_write": ("write", lambda a: {"port": a["port"], "data": a["data"]}),
    "serial_write_data": ("write", lambda a: {"port": a["port"], "data": a["data"]}),
    "serial_watch": (
        "watch",
        lambda a: {
            "port": a["port"],
            "duration": a.get("duration", 2.0),
            "expect": a.get("expect"),
            "idle_timeout": a.get("idle_timeout"),
            "start_seq": a.get("start_seq"),
            "from": a.get("from", "latest"),
            "regex": a.get("regex", False),
        },
    ),
    "serial_watch_port": (
        "watch",
        lambda a: {
            "port": a["port"],
            "duration": a.get("duration", 2.0),
            "expect": a.get("expect"),
            "idle_timeout": a.get("idle_timeout"),
            "start_seq": a.get("start_seq"),
            "from": a.get("from", "latest"),
            "regex": a.get("regex", False),
        },
    ),
    "serial_buffer_state": ("buffer_state", lambda a: {"port": a["port"]}),
    "serial_buffer": ("buffer_state", lambda a: {"port": a["port"]}),
    "serial_command": (
        "command",
        lambda a: {
            "port": a["port"],
            "command": a["command"],
            "expect": a.get("expect"),
            "duration": a.get("duration", a.get("timeout", 5.0)),
            "idle_timeout": a.get("idle_timeout", 0.3),
            "regex": a.get("regex", False),
        },
    ),
    "serial_send_command": (
        "command",
        lambda a: {
            "port": a["port"],
            "command": a["command"],
            "expect": a.get("expect"),
            "duration": a.get("duration", a.get("timeout", 5.0)),
            "idle_timeout": a.get("idle_timeout", 0.3),
            "regex": a.get("regex", False),
        },
    ),
    "serial_break": ("break", lambda a: {"port": a["port"]}),
    "serial_send_break": ("break", lambda a: {"port": a["port"]}),
    "serial_log": ("log", lambda a: {"port": a["port"], "lines": a.get("lines", 100)}),
    "serial_get_log_snapshot": (
        "log",
        lambda a: {"port": a["port"], "lines": a.get("lines", 100)},
    ),
    "serial_fetch_device_ip": (
        "fetch_device_ip",
        lambda a: {"port": a["port"], "timeout": a.get("timeout", 10)},
    ),
}


class MinimalMcpServer:
    """Minimal JSON-RPC stdio MCP tool adapter without external dependencies."""

    def __init__(self, client: SerialAccessApiClient):
        self.client = client

    def serve(self):
        for line in sys.stdin:
            if not line.strip():
                continue
            request = json.loads(line)
            response = self._handle(request)
            if response is not None:
                print(json.dumps(response, ensure_ascii=False), flush=True)

    def _handle(self, request):
        request_id = request.get("id")
        method = request.get("method", "")
        params = request.get("params", {})

        try:
            if method == "initialize":
                result = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "termlink", "version": "0.1.0"},
                }
            elif method == "tools/list":
                result = {"tools": TOOL_SCHEMAS}
            elif method == "tools/call":
                result = self._call_tool(params)
            elif method in ("notifications/initialized", "notifications/cancelled"):
                return None
            else:
                return self._error(request_id, -32601, f"Unknown method: {method}")
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        except Exception as exc:
            return self._error(request_id, -32603, str(exc))

    def _call_tool(self, params):
        name = params.get("name", "")
        arguments = params.get("arguments", {})
        if name not in ACTION_BY_TOOL:
            raise ValueError(f"Unknown tool: {name}")
        action, build_params = ACTION_BY_TOOL[name]
        response = self.client.request(action, build_params(arguments))
        return self._tool_response(response)

    @staticmethod
    def _tool_response(response):
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(response, ensure_ascii=False, indent=2),
                }
            ],
            "isError": response.get("code", 1) != 0,
        }

    @staticmethod
    def _error(request_id, code, message):
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        }


def main(argv=None):
    parser = argparse.ArgumentParser(description="TermLink MCP stdio server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=56337)
    parser.add_argument("--password", default="")
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args(argv)

    with SerialAccessApiClient(args.host, args.port, args.password, args.timeout, source="mcp") as client:
        MinimalMcpServer(client).serve()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

