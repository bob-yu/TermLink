import json
import socket
import threading
from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal

from .network_protocol import (
    MSG_TYPE_AUTH,
    MSG_TYPE_AUTH_RESULT,
    MSG_TYPE_BREAK,
    MSG_TYPE_DATA,
    MSG_TYPE_DEVICE_INFO,
    MSG_TYPE_LOG_DATA,
    MSG_TYPE_LOG_DOWNLOAD,
    MSG_TYPE_LOG_LIST,
    MSG_TYPE_LOG_LIST_RESPONSE,
    MSG_TYPE_PORT_ADD,
    MSG_TYPE_PORT_LIST,
    MSG_TYPE_PORT_REMOVE,
    MSG_TYPE_PORT_RENAME,
    MSG_TYPE_SELECT_PORT,
    MSG_TYPE_UNSELECT_PORT,
    decode_message,
    encode_message,
    extract_frames,
)


class SerialAccessClient(QObject):
    """GUI client for connecting to a SerialAccessServer."""

    connected = pyqtSignal()
    disconnected = pyqtSignal()
    port_list_received = pyqtSignal(list)
    port_added = pyqtSignal(str)
    port_removed = pyqtSignal(str)
    port_renamed = pyqtSignal(str, str)
    data_received = pyqtSignal(str, str)
    device_info_received = pyqtSignal(str, str, str)
    log_list_received = pyqtSignal(list)
    log_data_received = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, host: str, port: int, access_password: str = ""):
        super().__init__()
        self.host = host
        self.port = port
        self.access_password = access_password
        self._socket: Optional[socket.socket] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._connected = False
        self._selected_port = ""
        self._last_error = ""
        self._server_rejected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def last_error(self) -> str:
        return self._last_error

    def select_port(self, port: str):
        self._selected_port = port
        if self._connected:
            self._send_message(MSG_TYPE_SELECT_PORT, port, "")

    def unselect_port(self, port: str):
        if self._selected_port == port:
            self._selected_port = ""
        if self._connected:
            self._send_message(MSG_TYPE_UNSELECT_PORT, port, "")

    def connect_to_server(self):
        if self._running:
            return
        self._last_error = ""
        self._server_rejected = False
        self._running = True
        self._thread = threading.Thread(target=self._connect_and_receive, daemon=True)
        self._thread.start()

    def disconnect(self):
        self._running = False
        self._connected = False
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    def send(self, data: str):
        if not self._connected:
            return
        self._send_message(MSG_TYPE_DATA, self._selected_port, data)

    def send_to_port(self, port: str, data: str):
        if not self._connected:
            return
        self._send_message(MSG_TYPE_DATA, port, data)

    def send_break(self, port: str = ""):
        if not self._connected:
            return
        target_port = port or self._selected_port
        self._send_message(MSG_TYPE_BREAK, target_port, "")

    def request_log_list(self, log_dir: str):
        if not self._connected:
            return
        self._send_message(MSG_TYPE_LOG_LIST, "", log_dir)

    def download_log(self, log_dir: str, filename: str, offset: int = 0, chunk_size: int = 65536):
        if not self._connected:
            return
        request_data = json.dumps({
            "log_dir": log_dir,
            "filename": filename,
            "offset": offset,
            "chunk_size": chunk_size,
        })
        self._send_message(MSG_TYPE_LOG_DOWNLOAD, "", request_data)

    def _send_message(self, msg_type: int, port: str, data: str):
        if not self._socket:
            return
        try:
            msg = encode_message(msg_type, port, data)
            self._socket.sendall(msg)
        except Exception as exc:
            self.error_occurred.emit(f"Send failed: {exc}")

    def _connect_and_receive(self):
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(5.0)
            self._socket.connect((self.host, self.port))
            self._socket.settimeout(1.0)

            self._connected = True
            self._send_auth()
            self.connected.emit()

            buffer = b""
            while self._running:
                try:
                    data = self._socket.recv(4096)
                    if not data:
                        break

                    buffer += data
                    frames, buffer = extract_frames(buffer)

                    for msg_data in frames:
                        try:
                            msg = decode_message(msg_data)
                            self._handle_message(msg)
                        except Exception:
                            pass

                except socket.timeout:
                    continue
                except Exception:
                    break

        except Exception as exc:
            self._emit_error(f"Connection failed: {exc}")

        self._handle_disconnect()

    def _handle_message(self, msg: dict):
        msg_type = msg.get("type", 0)
        port = msg.get("port", "")
        data = msg.get("data", "")

        if msg_type == MSG_TYPE_DATA:
            self.data_received.emit(port, data)
        elif msg_type == MSG_TYPE_PORT_LIST:
            ports = json.loads(data) if data else []
            self.port_list_received.emit(ports)
        elif msg_type == MSG_TYPE_PORT_ADD:
            self.port_added.emit(port)
        elif msg_type == MSG_TYPE_PORT_REMOVE:
            self.port_removed.emit(port)
        elif msg_type == MSG_TYPE_PORT_RENAME:
            self.port_renamed.emit(port, data)
        elif msg_type == MSG_TYPE_DEVICE_INFO:
            try:
                info = json.loads(data) if data else {}
                version = info.get("version", "")
                ip = info.get("ip", "")
                self.device_info_received.emit(port, version, ip)
            except Exception:
                pass
        elif msg_type == MSG_TYPE_LOG_LIST_RESPONSE:
            files = json.loads(data) if data else []
            self.log_list_received.emit(files)
        elif msg_type == MSG_TYPE_LOG_DATA:
            log_data = json.loads(data) if data else {}
            if "data" in log_data:
                log_data["data"] = bytes.fromhex(log_data["data"])
            self.log_data_received.emit(log_data)
        elif msg_type == MSG_TYPE_AUTH_RESULT:
            try:
                result = json.loads(data) if data else {}
            except Exception:
                result = {}
            if result.get("authenticated") is False and not result.get("required"):
                message = result.get("message") or "Serial remote access denied"
                self._server_rejected = True
                self._emit_error(message)
                self._running = False
                if self._socket:
                    try:
                        self._socket.close()
                    except Exception:
                        pass

    def _emit_error(self, message: str):
        self._last_error = message
        self.error_occurred.emit(message)

    def _send_auth(self):
        self._send_message(MSG_TYPE_AUTH, "", json.dumps({"password": self.access_password}))

    def _handle_disconnect(self):
        was_connected = self._connected
        self._connected = False

        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None

        if was_connected:
            self.disconnected.emit()
