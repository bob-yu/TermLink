import os
import tempfile
import unittest

from core.log_manager import LogManager


class LogManagerTest(unittest.TestCase):
    def test_generate_filename_sanitizes_port_and_alias(self):
        manager = LogManager(
            log_dir="logs",
            name_pattern="{name}_{port}_{date}_{time}",
        )

        filename = manager.generate_filename("COM:3", "board/main")

        self.assertTrue(filename.endswith(".log"))
        self.assertIn("board_main", filename)
        self.assertIn("COM_3", filename)

    def test_get_stats_counts_only_log_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "a.log"), "wb") as f:
                f.write(b"x" * 1024)
            with open(os.path.join(tmp, "ignore.txt"), "wb") as f:
                f.write(b"x" * 2048)

            stats = LogManager(tmp).get_stats()

        self.assertEqual(stats["file_count"], 1)
        self.assertEqual(stats["total_size_mb"], 0.0)

    def test_check_rotation_returns_next_available_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "serial.log")
            with open(path, "wb") as f:
                f.write(b"x" * 2 * 1024 * 1024)
            with open(os.path.join(tmp, "serial_1.log"), "wb") as f:
                f.write(b"x")

            manager = LogManager(tmp, max_file_size_mb=1)
            rotated = manager.check_rotation(path)

        self.assertTrue(rotated.endswith("serial_2.log"))


if __name__ == "__main__":
    unittest.main()
