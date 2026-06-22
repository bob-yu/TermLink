import os
import tempfile
import unittest

from core.network_log_files import get_log_files, read_log_file_chunk


class NetworkLogFilesTest(unittest.TestCase):
    def test_get_log_files_returns_file_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "serial.log")
            with open(path, "wb") as f:
                f.write(b"abc")

            files = get_log_files(temp_dir)

            self.assertEqual(len(files), 1)
            self.assertEqual(files[0]["name"], "serial.log")
            self.assertEqual(files[0]["size"], 3)
            self.assertIn("mtime", files[0])

    def test_read_log_file_chunk(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "serial.log")
            with open(path, "wb") as f:
                f.write(b"0123456789")

            self.assertEqual(read_log_file_chunk(temp_dir, "serial.log", 2, 4), b"2345")

    def test_read_log_file_chunk_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError):
                read_log_file_chunk(temp_dir, "../outside.log")


if __name__ == "__main__":
    unittest.main()
