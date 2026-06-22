import unittest

from core.serial_access_protocol import (
    decode_service_payload,
    encode_service_message,
    recv_service_message,
)


class FakeSocket:
    def __init__(self, chunks):
        self._chunks = list(chunks)

    def recv(self, size):
        if not self._chunks:
            return b""
        chunk = self._chunks.pop(0)
        if len(chunk) <= size:
            return chunk
        self._chunks.insert(0, chunk[size:])
        return chunk[:size]


class SerialAccessProtocolTest(unittest.TestCase):
    def test_encode_decode_roundtrip(self):
        message = {"id": 1, "action": "list_ports", "params": {"text": "中文"}}
        frame = encode_service_message(message)

        self.assertEqual(decode_service_payload(frame[4:]), message)

    def test_recv_service_message_reads_chunked_socket(self):
        frame = encode_service_message({"id": 2, "action": "ping"})
        sock = FakeSocket([frame[:2], frame[2:5], frame[5:]])

        self.assertEqual(recv_service_message(sock), {"id": 2, "action": "ping"})

    def test_recv_service_message_returns_none_on_disconnect(self):
        sock = FakeSocket([b"\x00\x00"])

        self.assertIsNone(recv_service_message(sock))


if __name__ == "__main__":
    unittest.main()
