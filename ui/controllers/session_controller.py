class SessionController:
    """Batch operations for MainWindow session entries."""

    def __init__(self, sessions):
        self._sessions = sessions

    def connect_all(self) -> int:
        count = 0
        for worker, _tab, _config in self._sessions.values():
            if not getattr(worker, "is_connected", False) and hasattr(worker, "start"):
                worker.start()
                count += 1
        return count

    def disconnect_all(self) -> int:
        count = 0
        for worker, _tab, _config in self._sessions.values():
            if hasattr(worker, "stop"):
                worker.stop()
                count += 1
        return count

    def login_all(self) -> int:
        count = 0
        for worker, _tab, _config in self._sessions.values():
            if getattr(worker, "is_connected", False) and hasattr(worker, "start_login"):
                worker.start_login()
                count += 1
        return count
