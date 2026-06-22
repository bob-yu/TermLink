import importlib.util
from pathlib import Path
import unittest


def load_session_controller():
    path = Path(__file__).resolve().parents[1] / "ui" / "controllers" / "session_controller.py"
    spec = importlib.util.spec_from_file_location("session_controller_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SessionController


SessionController = load_session_controller()


class FakeWorker:
    def __init__(self, connected=False):
        self.is_connected = connected
        self.started = 0
        self.stopped = 0
        self.logins = 0

    def start(self):
        self.started += 1

    def stop(self):
        self.stopped += 1

    def start_login(self):
        self.logins += 1


class MinimalWorker:
    pass


class SessionControllerTest(unittest.TestCase):
    def test_connect_all_only_starts_disconnected_startable_workers(self):
        disconnected = FakeWorker(False)
        connected = FakeWorker(True)
        controller = SessionController({
            "a": (disconnected, None, None),
            "b": (connected, None, None),
            "c": (MinimalWorker(), None, None),
        })

        self.assertEqual(controller.connect_all(), 1)
        self.assertEqual(disconnected.started, 1)
        self.assertEqual(connected.started, 0)

    def test_disconnect_all_skips_workers_without_stop(self):
        worker = FakeWorker(True)
        controller = SessionController({
            "a": (worker, None, None),
            "b": (MinimalWorker(), None, None),
        })

        self.assertEqual(controller.disconnect_all(), 1)
        self.assertEqual(worker.stopped, 1)

    def test_login_all_only_logs_in_connected_login_capable_workers(self):
        connected = FakeWorker(True)
        disconnected = FakeWorker(False)
        controller = SessionController({
            "a": (connected, None, None),
            "b": (disconnected, None, None),
            "c": (MinimalWorker(), None, None),
        })

        self.assertEqual(controller.login_all(), 1)
        self.assertEqual(connected.logins, 1)
        self.assertEqual(disconnected.logins, 0)


if __name__ == "__main__":
    unittest.main()
