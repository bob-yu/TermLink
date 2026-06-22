import os
import tempfile
import unittest

from core.log_snapshot import read_last_lines


class LogSnapshotTest(unittest.TestCase):
    def test_read_last_lines(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "serial.log")
            with open(path, "w", encoding="utf-8") as f:
                f.write("one\n")
                f.write("two\n")
                f.write("three\n")

            self.assertEqual(read_last_lines(path, 2), "two\nthree\n")

    def test_missing_file_returns_empty_string(self):
        self.assertEqual(read_last_lines("missing.log", 10), "")

    def test_zero_lines_returns_empty_string(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            path = f.name
        try:
            self.assertEqual(read_last_lines(path, 0), "")
        finally:
            os.remove(path)


if __name__ == "__main__":
    unittest.main()
