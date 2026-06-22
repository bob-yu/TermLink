import sys
import types
import unittest


class _Signal:
    def __init__(self, *args, **kwargs):
        self._callbacks = []

    def connect(self, callback):
        self._callbacks.append(callback)

    def emit(self, *args):
        for callback in list(self._callbacks):
            callback(*args)


if "PyQt5" not in sys.modules:
    pyqt5 = types.ModuleType("PyQt5")
    qtcore = types.ModuleType("PyQt5.QtCore")

    class QObject:
        def __init__(self, *args, **kwargs):
            pass

    qtcore.QObject = QObject
    qtcore.pyqtSignal = _Signal
    sys.modules["PyQt5"] = pyqt5
    sys.modules["PyQt5.QtCore"] = qtcore

from core.network_protocol import MSG_TYPE_AUTH_RESULT, MSG_TYPE_UNSELECT_PORT, decode_message, extract_frames
from core.serial_access_client import SerialAccessClient


class SerialAccessClientTest(unittest.TestCase):
    def test_auth_denied_message_is_reported(self):
        client = SerialAccessClient("127.0.0.1", 56337)
        client._running = True
        errors = []
        client.error_occurred.connect(errors.append)

        client._handle_message({
            "type": MSG_TYPE_AUTH_RESULT,
            "port": "",
            "data": '{"authenticated": false, "required": false, "message": "Remote access denied: IP is banned"}',
        })

        self.assertEqual(errors, ["Remote access denied: IP is banned"])
        self.assertEqual(client.last_error, "Remote access denied: IP is banned")
        self.assertFalse(client._running)

    def test_unselect_port_sends_release_message(self):
        class FakeSocket:
            def __init__(self):
                self.data = b""

            def sendall(self, data):
                self.data += data

        fake_socket = FakeSocket()
        client = SerialAccessClient("127.0.0.1", 56337)
        client._socket = fake_socket
        client._connected = True
        client._selected_port = "COM12"

        client.unselect_port("COM12")

        frames, _remaining = extract_frames(fake_socket.data)
        self.assertEqual(client._selected_port, "")
        self.assertEqual(len(frames), 1)
        self.assertEqual(
            decode_message(frames[0]),
            {"type": MSG_TYPE_UNSELECT_PORT, "port": "COM12", "data": ""},
        )


if __name__ == "__main__":
    unittest.main()
