import socket
import threading
import unittest

from automation.serial_access_client import SerialAccessApiClient
from core.network_protocol import MSG_TYPE_AUTH_RESULT, encode_message
from core.serial_access_protocol import encode_service_message, recv_service_message


class AutomationClientTest(unittest.TestCase):
    def test_request_sends_action_and_password(self):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        host, port = listener.getsockname()
        received = {}

        def server():
            conn, _addr = listener.accept()
            with conn:
                received["message"] = recv_service_message(conn)
                conn.sendall(encode_service_message({"id": 1, "code": 0, "message": "ok"}))
            listener.close()

        thread = threading.Thread(target=server, daemon=True)
        thread.start()

        with SerialAccessApiClient(host, port, password="secret", source="cli") as client:
            response = client.request("list_ports")

        thread.join(timeout=2)
        self.assertEqual(response["code"], 0)
        self.assertEqual(received["message"]["action"], "list_ports")
        self.assertEqual(received["message"]["params"]["password"], "secret")
        self.assertEqual(received["message"]["params"]["source"], "cli")

    def test_watch_sends_from_parameter(self):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        host, port = listener.getsockname()
        received = {}

        def server():
            conn, _addr = listener.accept()
            with conn:
                received["message"] = recv_service_message(conn)
                conn.sendall(encode_service_message({"id": 1, "code": 0, "message": "ok"}))
            listener.close()

        thread = threading.Thread(target=server, daemon=True)
        thread.start()

        with SerialAccessApiClient(host, port) as client:
            response = client.watch("COM1", start_seq=10, from_position="seq")

        thread.join(timeout=2)
        self.assertEqual(response["code"], 0)
        self.assertEqual(received["message"]["action"], "watch")
        self.assertEqual(received["message"]["params"]["from"], "seq")
        self.assertEqual(received["message"]["params"]["start_seq"], 10)

    def test_request_reports_server_rejection_message(self):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        host, port = listener.getsockname()

        def server():
            conn, _addr = listener.accept()
            with conn:
                recv_service_message(conn)
                conn.sendall(encode_message(
                    MSG_TYPE_AUTH_RESULT,
                    "",
                    '{"authenticated": false, "required": false, "message": "Remote access denied: IP is banned"}',
                ))
            listener.close()

        thread = threading.Thread(target=server, daemon=True)
        thread.start()

        with SerialAccessApiClient(host, port) as client:
            with self.assertRaisesRegex(ConnectionError, "IP is banned"):
                client.request("list")

        thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
