import socket
from typing import Optional


class SimpleTelnet:
    IAC = 255
    DONT = 254
    DO = 253
    WONT = 252
    WILL = 251
    SB = 250
    SE = 240

    def __init__(self, host: str = None, port: int = 23, timeout: float = 10):
        self._sock: Optional[socket.socket] = None
        self._buffer = b""
        self._timeout = timeout

        if host:
            self.open(host, port, timeout)

    def open(self, host: str, port: int = 23, timeout: float = 10):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(timeout)
        self._sock.connect((host, port))
        self._sock.settimeout(0.1)

    def close(self):
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    def write(self, data: bytes):
        if self._sock:
            self._sock.sendall(data)

    def read_very_eager(self) -> bytes:
        if not self._sock:
            return b""

        result = b""
        try:
            while True:
                chunk = self._sock.recv(4096)
                if not chunk:
                    raise EOFError("Connection closed")
                result += self._process_telnet_commands(chunk)
        except socket.timeout:
            pass
        except BlockingIOError:
            pass

        return result

    def read_until(self, match: bytes, timeout: float = None) -> bytes:
        if not self._sock:
            return b""

        old_timeout = self._sock.gettimeout()
        if timeout:
            self._sock.settimeout(timeout)

        result = b""
        try:
            while match not in result:
                chunk = self._sock.recv(1024)
                if not chunk:
                    break
                result += self._process_telnet_commands(chunk)
        except socket.timeout:
            pass
        finally:
            self._sock.settimeout(old_timeout)

        return result

    def _process_telnet_commands(self, data: bytes) -> bytes:
        result = b""
        i = 0
        while i < len(data):
            if data[i] == self.IAC and i + 1 < len(data):
                cmd = data[i + 1]
                if cmd in (self.DO, self.DONT, self.WILL, self.WONT):
                    if i + 2 < len(data):
                        option = data[i + 2]
                        if cmd == self.DO:
                            self._send_command(self.WONT, option)
                        elif cmd == self.WILL:
                            self._send_command(self.DONT, option)
                        i += 3
                        continue
                elif cmd == self.IAC:
                    result += bytes([self.IAC])
                    i += 2
                    continue
                elif cmd == self.SB:
                    end = data.find(bytes([self.IAC, self.SE]), i)
                    if end != -1:
                        i = end + 2
                        continue
                    break
                else:
                    i += 2
                    continue
            else:
                result += bytes([data[i]])
                i += 1

        return result

    def _send_command(self, cmd: int, option: int):
        if self._sock:
            try:
                self._sock.sendall(bytes([self.IAC, cmd, option]))
            except Exception:
                pass
