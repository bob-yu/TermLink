import tempfile
import unittest

from core.serial_access_service import SerialAccessService
from core.serial_output_buffer import SerialOutputBuffer
from core.serial_access_protocol import (
    ERR_BAD_PARAMS,
    ERR_OK,
    ERR_PORT_NOT_FOUND,
    ERR_PORT_NOT_OPEN,
)


class FakeState:
    def __init__(self):
        self.device_ip = "10.0.0.2"
        self.checked = False

    def check_hung(self):
        self.checked = True


class FakeWorker:
    def __init__(self, connected=True):
        self.is_connected = connected
        self.source_id = "src-COM1"
        self._device_state = FakeState()
        self.written = []
        self.commands = []
        self.breaks = 0
        self._log_file = tempfile.NamedTemporaryFile("w", delete=False)
        self._log_file.write("a\nb\nc\n")
        self._log_file.close()
        self.log_filepath = self._log_file.name

    def get_full_device_state(self):
        return {
            "physical_state": "CONNECTED" if self.is_connected else "DISCONNECTED",
            "device_run_state": "READY",
            "device_ip": self._device_state.device_ip,
            "device_version": "v1",
        }

    def write(self, data):
        self.written.append(data)

    def send_command(self, command):
        self.commands.append(command)

    def send_break(self):
        self.breaks += 1


class FakeConfig:
    name = "DUT"


class SerialAccessServiceTest(unittest.TestCase):
    def setUp(self):
        self.worker = FakeWorker()
        self.sessions = {
            "COM1": (self.worker, None, FakeConfig()),
            "remote://COM2": (FakeWorker(), None, FakeConfig()),
        }
        self.output_buffer = SerialOutputBuffer()
        self.service = SerialAccessService(lambda: self.sessions, self.output_buffer)

    def test_list_ports_excludes_remote_sessions(self):
        result = self.service.list_ports()

        self.assertEqual(result["code"], ERR_OK)
        self.assertEqual(len(result["data"]), 1)
        self.assertEqual(result["data"][0]["port"], "COM1")

    def test_write_requires_open_port(self):
        self.sessions["COM1"] = (FakeWorker(connected=False), None, FakeConfig())

        result = self.service.write("COM1", "help\n")

        self.assertEqual(result["code"], ERR_PORT_NOT_OPEN)

    def test_write_to_existing_port(self):
        result = self.service.write("COM1", "help\n")

        self.assertEqual(result["code"], ERR_OK)
        self.assertEqual(self.worker.written, ["help\n"])

    def test_watch_reads_from_output_buffer(self):
        start_seq = self.output_buffer.latest_seq("COM1")
        self.output_buffer.append("COM1", "boot ok#")

        result = self.service.watch("COM1", duration=0.01, expect="#", start_seq=start_seq, from_position="seq")

        self.assertEqual(result["code"], ERR_OK)
        self.assertEqual(result["data"]["reason"], "expect")
        self.assertEqual(result["data"]["output"], "boot ok#")

    def test_watch_from_oldest_reads_existing_buffer(self):
        self.output_buffer.append("COM1", "boot ok#")

        result = self.service.watch("COM1", duration=0.01, from_position="oldest")

        self.assertEqual(result["code"], ERR_OK)
        self.assertEqual(result["data"]["output"], "boot ok#")

    def test_buffer_state_returns_seq_range(self):
        self.output_buffer.append("COM1", "boot")

        result = self.service.buffer_state("COM1")

        self.assertEqual(result["code"], ERR_OK)
        self.assertEqual(result["data"]["port"], "COM1")
        self.assertEqual(result["data"]["oldest_seq"], 1)
        self.assertEqual(result["data"]["latest_seq"], 1)

    def test_command_reads_output_after_write_start_seq(self):
        original_send = self.worker.send_command

        def send_command(command):
            original_send(command)
            self.output_buffer.append("COM1", "answer#")

        self.worker.send_command = send_command

        result = self.service.send_command("COM1", "cmd", expect="#", duration=0.1)

        self.assertEqual(result["code"], ERR_OK)
        self.assertEqual(self.worker.commands, ["cmd"])
        self.assertEqual(result["data"]["output"], "answer#")

    def test_find_ports_by_ip(self):
        result = self.service.find_ports("10.0.0.2")

        self.assertEqual(result["code"], ERR_OK)
        self.assertEqual(result["data"]["port"], "COM1")

    def test_find_ports_missing_param(self):
        result = self.service.find_ports("")

        self.assertEqual(result["code"], ERR_BAD_PARAMS)

    def test_unknown_port(self):
        result = self.service.get_port_state("COM9")

        self.assertEqual(result["code"], ERR_PORT_NOT_FOUND)

    def test_update_device_info(self):
        result = self.service.update_device_info("COM1", device_ip="10.0.0.9")

        self.assertEqual(result["code"], ERR_OK)
        self.assertEqual(self.worker._device_state.device_ip, "10.0.0.9")

    def test_hung_check_skips_remote_sessions(self):
        remote_worker = self.sessions["remote://COM2"][0]

        self.service.check_hung_ports()

        self.assertTrue(self.worker._device_state.checked)
        self.assertFalse(remote_worker._device_state.checked)


if __name__ == "__main__":
    unittest.main()
