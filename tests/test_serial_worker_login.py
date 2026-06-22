import unittest
import sys

from core.login_state_machine import LoginConfig

if "PyQt5.QtCore" in sys.modules and not hasattr(sys.modules["PyQt5.QtCore"], "QTimer"):
    for name in list(sys.modules):
        if name == "PyQt5" or name.startswith("PyQt5."):
            del sys.modules[name]

from core.serial_worker import SerialConfig, SerialWorker, WorkerState  # noqa: E402


class SerialWorkerLoginTest(unittest.TestCase):
    def test_setup_login_does_not_enable_auto_login(self):
        worker = SerialWorker(SerialConfig("COM_TEST"), log_enabled=False)

        worker.setup_login(LoginConfig(username="root"))

        self.assertFalse(worker._auto_login_enabled)

    def test_request_device_info_does_not_send_login_when_not_logged_in(self):
        worker = SerialWorker(SerialConfig("COM_TEST"), log_enabled=False)
        worker.setup_login(LoginConfig(username="root"))
        worker.state = WorkerState.CONNECTED

        worker.request_device_info()

        self.assertTrue(worker._write_queue.empty())


if __name__ == "__main__":
    unittest.main()
