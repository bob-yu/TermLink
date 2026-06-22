import unittest

from ui.main_window import MainWindow


class FakeTabWidget:
    def __init__(self, tab):
        self._tab = tab
        self.removed = []

    def widget(self, index):
        return self._tab

    def removeTab(self, index):
        self.removed.append(index)


class FakeStatusBar:
    def __init__(self):
        self.messages = []

    def showMessage(self, message):
        self.messages.append(message)


class FakeRemoteSessions:
    def __init__(self):
        self.closed_keys = []

    def close_session_by_key(self, key):
        self.closed_keys.append(key)
        return True


class FakeTab:
    pass


class FakeWorker:
    def __init__(self):
        self.stopped = False

    def stop(self):
        self.stopped = True


class MainWindowCloseTabTest(unittest.TestCase):
    def test_remote_tab_close_uses_remote_session_controller(self):
        window = MainWindow.__new__(MainWindow)
        tab = FakeTab()
        worker = FakeWorker()
        remote_key = "remote://127.0.0.1:56337/COM12"
        window._sessions = {remote_key: (worker, tab, None)}
        window.tab_widget = FakeTabWidget(tab)
        window._remote_serial_sessions = FakeRemoteSessions()
        window.statusbar = FakeStatusBar()

        window._close_tab(0)

        self.assertEqual(window._remote_serial_sessions.closed_keys, [remote_key])
        self.assertIn(remote_key, window._sessions)
        self.assertFalse(worker.stopped)
        self.assertEqual(window.tab_widget.removed, [])


if __name__ == "__main__":
    unittest.main()
