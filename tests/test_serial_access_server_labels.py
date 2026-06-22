import unittest

from core.network_protocol import MSG_TYPE_SELECT_PORT, MSG_TYPE_UNSELECT_PORT
from core.serial_access_server import SerialAccessServer


class SerialAccessServerLabelsTest(unittest.TestCase):
    def test_client_port_labels_hide_clients_without_open_ports(self):
        server = SerialAccessServer(
            "127.0.0.1",
            56337,
            "logs",
            sessions_provider=lambda: {},
        )

        with server._lock:
            server._clients["10.0.0.5:41000"] = object()
            server._clients["10.0.0.6:41001"] = object()
            server._client_selected_port["10.0.0.5:41000"] = "COM12"

        self.assertEqual(
            server.client_port_labels,
            [],
        )

    def test_client_port_labels_include_multiple_open_ports(self):
        server = SerialAccessServer(
            "127.0.0.1",
            56337,
            "logs",
            sessions_provider=lambda: {},
        )

        with server._lock:
            server._clients["10.0.0.5:41000"] = object()
            server._client_open_ports["10.0.0.5:41000"] = {"COM12", "COM5"}

        self.assertEqual(
            server.client_port_labels,
            ["10.0.0.5:41000:COM12 [read-write]", "10.0.0.5:41000:COM5 [read-write]"],
        )

    def test_select_port_updates_multiple_open_port_labels(self):
        server = SerialAccessServer(
            "127.0.0.1",
            56337,
            "logs",
            sessions_provider=lambda: {},
        )
        updated = []
        server.client_updated.connect(lambda addr: updated.append(addr))

        with server._lock:
            server._clients["10.0.0.5:41000"] = object()
            server._client_authorized["10.0.0.5:41000"] = True

        server._handle_client_message("10.0.0.5:41000", {"type": MSG_TYPE_SELECT_PORT, "port": "COM12", "data": ""})
        server._handle_client_message("10.0.0.5:41000", {"type": MSG_TYPE_SELECT_PORT, "port": "COM5", "data": ""})

        self.assertEqual(
            server.client_port_labels,
            ["10.0.0.5:41000:COM12 [read-write]", "10.0.0.5:41000:COM5 [read-write]"],
        )
        self.assertEqual(updated, ["10.0.0.5:41000", "10.0.0.5:41000"])

    def test_unselect_port_removes_only_that_proxy_label(self):
        server = SerialAccessServer(
            "127.0.0.1",
            56337,
            "logs",
            sessions_provider=lambda: {},
        )
        updated = []
        server.client_updated.connect(lambda addr: updated.append(addr))

        with server._lock:
            server._clients["10.0.0.5:41000"] = object()
            server._client_authorized["10.0.0.5:41000"] = True
            server._client_selected_port["10.0.0.5:41000"] = "COM5"
            server._client_open_ports["10.0.0.5:41000"] = {"COM12", "COM5"}

        server._handle_client_message(
            "10.0.0.5:41000",
            {"type": MSG_TYPE_UNSELECT_PORT, "port": "COM12", "data": ""},
        )

        self.assertEqual(
            server.client_port_labels,
            ["10.0.0.5:41000:COM5 [read-write]"],
        )
        self.assertEqual(updated, ["10.0.0.5:41000"])


if __name__ == "__main__":
    unittest.main()
