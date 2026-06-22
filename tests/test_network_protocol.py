import unittest

from core.network_protocol import (
    MSG_TYPE_AUTH,
    MSG_TYPE_DATA,
    decode_message,
    encode_message,
    extract_frames,
)


class NetworkProtocolTest(unittest.TestCase):
    def test_encode_decode_roundtrip(self):
        frame = encode_message(MSG_TYPE_DATA, "COM3", "hello")

        self.assertEqual(int.from_bytes(frame[:4], "big"), len(frame) - 4)
        self.assertEqual(
            decode_message(frame[4:]),
            {"type": MSG_TYPE_DATA, "port": "COM3", "data": "hello"},
        )

    def test_text_payload(self):
        frame = encode_message(MSG_TYPE_DATA, "COM3", "sample text")

        self.assertEqual(decode_message(frame[4:])["data"], "sample text")

    def test_auth_message_roundtrip(self):
        frame = encode_message(MSG_TYPE_AUTH, "", '{"password":"secret"}')

        self.assertEqual(decode_message(frame[4:])["type"], MSG_TYPE_AUTH)

    def test_extract_frames_keeps_partial_tail(self):
        frame1 = encode_message(MSG_TYPE_DATA, "COM1", "one")
        frame2 = encode_message(MSG_TYPE_DATA, "COM2", "two")
        partial = frame2[:6]

        frames, rest = extract_frames(frame1 + partial)

        self.assertEqual(len(frames), 1)
        self.assertEqual(decode_message(frames[0])["data"], "one")
        self.assertEqual(rest, partial)

    def test_extract_frames_handles_multiple_frames(self):
        frame1 = encode_message(MSG_TYPE_DATA, "COM1", "one")
        frame2 = encode_message(MSG_TYPE_DATA, "COM2", "two")

        frames, rest = extract_frames(frame1 + frame2)

        self.assertEqual(
            [decode_message(frame)["port"] for frame in frames],
            ["COM1", "COM2"],
        )
        self.assertEqual(rest, b"")


if __name__ == "__main__":
    unittest.main()
