import unittest
import sys
import types


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

from core.serial_access_server import SerialAccessServer
from core.network_protocol import MSG_TYPE_AUTH, MSG_TYPE_DATA
from core.serial_access_protocol import ERR_OK


class FakeSocket:
    def __init__(self):
        self.sent = []
        self.closed = False

    def sendall(self, data):
        self.sent.append(data)

    def close(self):
        self.closed = True


class FakeState:
    device_ip = "10.0.0.2"

    def check_hung(self):
        pass


class FakeWorker:
    is_connected = True
    source_id = "src-COM1"
    log_filepath = ""

    def __init__(self):
        self._device_state = FakeState()
        self.writes = []

    def get_full_device_state(self):
        return {
            "physical_state": "CONNECTED",
            "device_run_state": "READY",
            "device_ip": "10.0.0.2",
            "device_version": "v1",
        }

    def write(self, data):
        self.writes.append(data)


class FakeConfig:
    name = "DUT"


class NetworkSerialAccessApiTest(unittest.TestCase):
    def setUp(self):
        self.worker = FakeWorker()
        self.server = SerialAccessServer(
            sessions_provider=lambda: {"COM1": (self.worker, None, FakeConfig())}
        )
        self.socket = FakeSocket()
        self.server._clients["client"] = self.socket
        self.server._client_authorized["client"] = True

    def test_gui_protocol_message_still_routes_to_signal(self):
        received = []
        self.server.data_received.connect(lambda addr, port, data: received.append((addr, port, data)))

        self.server._handle_client_message("client", {"type": MSG_TYPE_DATA, "port": "COM1", "data": "x"})

        self.assertEqual(received, [("client", "COM1", "x")])

    def test_read_only_client_cannot_write_gui_protocol(self):
        received = []
        self.server.data_received.connect(lambda addr, port, data: received.append((addr, port, data)))
        self.server.set_client_permission("client", "read-only")

        self.server._handle_client_message("client", {"type": MSG_TYPE_DATA, "port": "COM1", "data": "x"})

        self.assertEqual(received, [])

    def test_read_only_client_cannot_write_action_protocol(self):
        self.server.set_client_permission("client", "read-only")

        self.server._handle_client_message(
            "client",
            {"id": 11, "action": "write", "params": {"port": "COM1", "data": "x"}},
        )

        self.assertIn(b"read-only", self.socket.sent[0])

    def test_ban_ip_disconnects_matching_clients(self):
        self.server._clients["10.0.0.5:41000"] = FakeSocket()
        self.server._client_authorized["10.0.0.5:41000"] = True

        self.assertTrue(self.server.ban_ip("10.0.0.5"))

        self.assertNotIn("10.0.0.5:41000", self.server._clients)
        self.assertIn("10.0.0.5", self.server.banned_ips)

    def test_action_protocol_uses_same_server(self):
        self.server._handle_client_message("client", {"id": 7, "action": "list_ports", "params": {}})

        self.assertEqual(len(self.socket.sent), 1)
        self.assertIn(b'"id": 7', self.socket.sent[0])
        self.assertIn(f'"code": {ERR_OK}'.encode("utf-8"), self.socket.sent[0])
        self.assertIn(b'"port": "COM1"', self.socket.sent[0])

    def test_password_blocks_gui_messages_until_authenticated(self):
        self.server.access_password = "secret"
        self.server._client_authorized["client"] = False
        received = []
        self.server.data_received.connect(lambda addr, port, data: received.append((addr, port, data)))

        self.server._handle_client_message("client", {"type": MSG_TYPE_DATA, "port": "COM1", "data": "x"})
        self.server._handle_client_message(
            "client",
            {"type": MSG_TYPE_AUTH, "port": "", "data": '{"password": "secret"}'},
        )
        self.server._handle_client_message("client", {"type": MSG_TYPE_DATA, "port": "COM1", "data": "x"})

        self.assertEqual(received, [("client", "COM1", "x")])

    def test_bad_password_disconnects_gui_client(self):
        self.server.access_password = "secret"
        self.server._client_authorized["client"] = False

        self.server._handle_client_message(
            "client",
            {"type": MSG_TYPE_AUTH, "port": "", "data": '{"password": "bad"}'},
        )

        self.assertNotIn("client", self.server._clients)
        self.assertTrue(self.socket.closed)
        self.assertIn(b"invalid password", self.socket.sent[0])

    def test_password_blocks_action_protocol_until_authenticated(self):
        self.server.access_password = "secret"
        self.server._client_authorized["client"] = False

        self.server._handle_client_message("client", {"id": 8, "action": "list_ports", "params": {}})
        self.server._handle_client_message(
            "client",
            {"id": 9, "action": "list_ports", "params": {"password": "secret"}},
        )

        self.assertIn(b"Authentication required", self.socket.sent[0])
        self.assertIn(b'"id": 9', self.socket.sent[-1])
        self.assertIn(b'"port": "COM1"', self.socket.sent[-1])

    def test_unauthorized_clients_do_not_receive_broadcasts(self):
        self.server._client_authorized["client"] = False

        self.server.broadcast_port_list()
        self.server.on_serial_data("COM1", "data")

        self.assertEqual(self.socket.sent, [])

    def test_watch_action_reads_serial_output_buffer(self):
        self.server.on_serial_data("COM1", "data#")
        self.socket.sent.clear()

        self.server._handle_client_message(
            "client",
            {
                "id": 10,
                "action": "watch",
                "params": {"port": "COM1", "duration": 0.01, "expect": "#", "start_seq": 0},
            },
        )

        self.assertIn(b'"id": 10', self.socket.sent[0])
        self.assertIn(b'"reason": "expect"', self.socket.sent[0])
        self.assertIn(b"data#", self.socket.sent[0])


if __name__ == "__main__":
    unittest.main()
