import socket
import time
from typing import Optional

from core.network_protocol import MSG_TYPE_AUTH_RESULT
from core.serial_access_protocol import encode_service_message, recv_service_message


class SerialAccessApiClient:
    """Small synchronous client for the Serial Access action API."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 56337,
        password: str = "",
        timeout: float = 10.0,
        source: str = "",
    ):
        self.host = host
        self.port = port
        self.password = password
        self.timeout = timeout
        self.source = source
        self._sock: Optional[socket.socket] = None
        self._next_id = 1

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, _exc_type, _exc, _tb):
        self.close()

    def connect(self):
        if self._sock:
            return
        try:
            self._sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
            self._sock.settimeout(self.timeout)
        except OSError as exc:
            raise ConnectionError(f"Cannot connect to serial access server {self.host}:{self.port}: {exc}") from exc

    def close(self):
        if not self._sock:
            return
        try:
            self._sock.close()
        finally:
            self._sock = None

    def request(self, action: str, params: Optional[dict] = None) -> dict:
        if not self._sock:
            self.connect()
        params = dict(params or {})
        if self.password and "password" not in params:
            params["password"] = self.password
        if self.source and "source" not in params:
            params["source"] = self.source
        request_id = self._next_id
        self._next_id += 1
        self._sock.sendall(encode_service_message({
            "id": request_id,
            "action": action,
            "params": params,
        }))
        while True:
            response = recv_service_message(self._sock)
            if response is None:
                raise ConnectionError("Serial access server closed the connection")
            self._raise_if_rejected(response)
            if response.get("id") == request_id:
                return response

    @staticmethod
    def _raise_if_rejected(message: dict):
        if message.get("type") != MSG_TYPE_AUTH_RESULT:
            return
        data = message.get("data", "")
        try:
            import json
            result = json.loads(data) if data else {}
        except Exception:
            result = {}
        if result.get("authenticated") is False and not result.get("required"):
            raise ConnectionError(result.get("message") or "Serial remote access denied")

    def subscribe(self, port: str) -> dict:
        return self.request("subscribe", {"port": port})

    def watch(
        self,
        port: str,
        duration: float = 2.0,
        expect: Optional[str] = None,
        idle_timeout: Optional[float] = None,
        start_seq: Optional[int] = None,
        from_position: str = "latest",
        regex: bool = False,
    ) -> dict:
        params = {
            "port": port,
            "duration": duration,
            "expect": expect,
            "idle_timeout": idle_timeout,
            "start_seq": start_seq,
            "from": from_position,
            "regex": regex,
        }
        return self.request("watch", params)

    def buffer_state(self, port: str) -> dict:
        return self.request("buffer_state", {"port": port})

    def recv_event(self) -> Optional[dict]:
        if not self._sock:
            self.connect()
        while True:
            message = recv_service_message(self._sock)
            if message is None:
                return None
            if message.get("event"):
                return message

    def collect_events(self, duration: float, port: str = "") -> list:
        if not self._sock:
            self.connect()
        events = []
        deadline = time.monotonic() + max(0.0, duration)
        original_timeout = self._sock.gettimeout()
        try:
            while time.monotonic() < deadline:
                self._sock.settimeout(max(0.05, deadline - time.monotonic()))
                try:
                    message = recv_service_message(self._sock)
                except socket.timeout:
                    break
                if message is None:
                    break
                if not message.get("event"):
                    continue
                data = message.get("data", {})
                if port and data.get("port") != port:
                    continue
                events.append(message)
        finally:
            self._sock.settimeout(original_timeout)
        return events

    def send_and_watch(self, port: str, data: str, duration: float = 2.0) -> dict:
        write_response = self.request("write", {"port": port, "data": data})
        watch_response = self.watch(port, duration=duration)
        return {
            "code": write_response.get("code", 1),
            "message": write_response.get("message", ""),
            "data": {
                "write": write_response,
                "watch": watch_response,
            },
        }
