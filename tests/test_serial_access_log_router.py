import json
import tempfile
import unittest
from pathlib import Path

from core.network_protocol import MSG_TYPE_LOG_DATA, MSG_TYPE_LOG_LIST_RESPONSE, decode_message
from core.serial_access_log_router import SerialAccessLogRouter


class SerialAccessLogRouterTest(unittest.TestCase):
    def test_lists_files_from_server_log_dir(self):
        sent = []
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "app.log").write_text("hello", encoding="utf-8")
            router = SerialAccessLogRouter(lambda: tmp, lambda *args: sent.append(args), lambda _msg: None)

            router.handle_list_request("client")

        self.assertEqual(sent[0][1], MSG_TYPE_LOG_LIST_RESPONSE)
        files = json.loads(sent[0][3])
        self.assertEqual(files[0]["name"], "app.log")

    def test_downloads_file_chunk(self):
        sent = []
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "app.log").write_bytes(b"abcdef")
            router = SerialAccessLogRouter(lambda: tmp, lambda *args: sent.append(args), lambda _msg: None)

            router.handle_download_request(
                "client",
                json.dumps({"filename": "app.log", "offset": 2, "chunk_size": 3}),
            )

        self.assertEqual(sent[0][1], MSG_TYPE_LOG_DATA)
        payload = json.loads(sent[0][3])
        self.assertEqual(bytes.fromhex(payload["data"]), b"cde")

    def test_invalid_download_emits_error(self):
        errors = []
        router = SerialAccessLogRouter(lambda: "missing", lambda *args: None, errors.append)

        router.handle_download_request("client", json.dumps({"filename": "no.log"}))

        self.assertEqual(len(errors), 1)


if __name__ == "__main__":
    unittest.main()
