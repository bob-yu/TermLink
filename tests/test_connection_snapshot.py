import unittest
import importlib.util
from pathlib import Path

_snapshot_path = Path(__file__).resolve().parents[1] / "ui" / "connection_snapshot.py"
_spec = importlib.util.spec_from_file_location("connection_snapshot_under_test", _snapshot_path)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
AccessSnapshot = _module.AccessSnapshot
ConnectionSnapshot = _module.ConnectionSnapshot
SessionSnapshot = _module.SessionSnapshot


class ConnectionSnapshotTest(unittest.TestCase):
    def test_snapshot_holds_session_and_access_state(self):
        snapshot = ConnectionSnapshot(
            sessions=[
                SessionSnapshot("COM1", "DUT", True, "local"),
                SessionSnapshot("remote://COM2", "Remote", False, "remote"),
            ],
            access=AccessSnapshot(
                summary="Sessions: 2, connected: 1",
                details=["Remote access server: 0.0.0.0:56337"],
                clients=["10.0.0.3:51000"],
            ),
        )

        self.assertEqual(snapshot.sessions[0].kind, "local")
        self.assertEqual(snapshot.sessions[1].kind, "remote")
        self.assertEqual(snapshot.access.summary, "Sessions: 2, connected: 1")
        self.assertEqual(snapshot.access.clients, ["10.0.0.3:51000"])


if __name__ == "__main__":
    unittest.main()
