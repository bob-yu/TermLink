import unittest

from core.scrollback_buffer import ScrollbackBuffer


class ScrollbackBufferTest(unittest.TestCase):
    def test_discards_oldest_lines(self):
        buffer = ScrollbackBuffer(max_lines=2)

        buffer.append("one")
        buffer.append("two")
        buffer.append("three")

        self.assertEqual(len(buffer), 2)
        self.assertEqual(buffer.get_lines(0, 2), ["two", "three"])

    def test_resize_preserves_newest_lines(self):
        buffer = ScrollbackBuffer(max_lines=4)
        for item in ["one", "two", "three"]:
            buffer.append(item)

        buffer.max_lines = 2

        self.assertEqual(buffer.get_lines(0, 2), ["two", "three"])

    def test_get_line_out_of_range(self):
        buffer = ScrollbackBuffer(max_lines=2)

        self.assertEqual(buffer.get_line(99), "")


if __name__ == "__main__":
    unittest.main()
