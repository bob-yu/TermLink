import threading
import time
import unittest

from core.serial_output_buffer import SerialOutputBuffer


class SerialOutputBufferTest(unittest.TestCase):
    def test_watch_returns_on_expect(self):
        buffer = SerialOutputBuffer()
        start_seq = buffer.latest_seq("COM1")

        def writer():
            time.sleep(0.02)
            buffer.append("COM1", "login: ")
            buffer.append("COM1", "root#")

        thread = threading.Thread(target=writer)
        thread.start()
        result = buffer.watch("COM1", start_seq=start_seq, duration=1.0, expect="#")
        thread.join(timeout=1)

        self.assertEqual(result["reason"], "expect")
        self.assertTrue(result["matched"])
        self.assertIn("root#", result["output"])

    def test_watch_returns_on_idle_after_data(self):
        buffer = SerialOutputBuffer()
        start_seq = buffer.latest_seq("COM1")

        def writer():
            time.sleep(0.02)
            buffer.append("COM1", "ready")

        thread = threading.Thread(target=writer)
        thread.start()
        result = buffer.watch("COM1", start_seq=start_seq, duration=1.0, idle_timeout=0.03)
        thread.join(timeout=1)

        self.assertEqual(result["reason"], "idle_timeout")
        self.assertEqual(result["output"], "ready")

    def test_watch_reports_overrun(self):
        buffer = SerialOutputBuffer(max_bytes_per_port=8)
        start_seq = buffer.latest_seq("COM1")
        buffer.append("COM1", "one")
        buffer.append("COM1", "two")
        buffer.append("COM1", "three")

        result = buffer.watch("COM1", start_seq=start_seq, duration=0.01)

        self.assertTrue(result["lost"])
        self.assertEqual(result["output"], "twothree")

    def test_watch_from_oldest_reads_current_buffer(self):
        buffer = SerialOutputBuffer()
        buffer.append("COM1", "one")
        buffer.append("COM1", "two")

        result = buffer.watch("COM1", from_position="oldest", duration=0.01)

        self.assertFalse(result["lost"])
        self.assertEqual(result["output"], "onetwo")

    def test_state_reports_drop_counters_and_seq_range(self):
        buffer = SerialOutputBuffer(max_bytes_per_port=8)
        buffer.append("COM1", "one")
        buffer.append("COM1", "two")
        buffer.append("COM1", "three")

        state = buffer.state("COM1")

        self.assertEqual(state["max_bytes"], 8)
        self.assertEqual(state["current_bytes"], len("twothree"))
        self.assertEqual(state["oldest_seq"], 2)
        self.assertEqual(state["latest_seq"], 3)
        self.assertEqual(state["dropped_chunks"], 1)
        self.assertEqual(state["dropped_bytes"], len("one"))
        self.assertGreater(state["last_drop_time"], 0)


if __name__ == "__main__":
    unittest.main()
