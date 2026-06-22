"""Asynchronous data bus for serial, network, and log data."""

import queue
import threading
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, Dict, List, Optional

from PyQt5.QtCore import QCoreApplication, QObject, QThread, QTimer, pyqtSignal


class MessageType(Enum):
    """Message type."""

    DATA = auto()
    STATE_CHANGE = auto()
    ERROR = auto()
    LOG = auto()


@dataclass
class Message:
    """Data-bus message."""

    msg_type: MessageType
    source: str
    data: str
    timestamp: float = 0


class DataBus(QObject):
    """Core async dispatcher.

    I/O threads publish text into source-specific buffers. The UI thread flushes
    those buffers in batches to reduce signal churn, while a separate log queue
    lets log writing avoid blocking terminal rendering.
    """

    batch_data_ready = pyqtSignal(dict)

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    cls._instance = instance
        return cls._instance

    def __init__(self):
        if DataBus._initialized:
            return
        super().__init__()
        DataBus._initialized = True

        self._queue = queue.Queue()
        self._buffers: Dict[str, str] = {}
        self._buffer_lock = threading.Lock()
        self._subscribers: Dict[str, List[Callable]] = {}

        self._dispatch_timer = None
        app = QCoreApplication.instance()
        if app is not None and QThread.currentThread() == app.thread():
            self._dispatch_timer = QTimer(self)
            self._dispatch_timer.timeout.connect(self._dispatch_batch)
            self._dispatch_timer.start(16)

        self._log_queue = queue.Queue()
        self._log_thread: Optional[threading.Thread] = None
        self._log_running = False
        self._log_handlers: Dict[str, Callable] = {}

    def start_log_thread(self):
        """Start the log worker thread."""
        if self._log_running:
            return
        self._log_running = True
        self._log_thread = threading.Thread(target=self._log_worker, daemon=True)
        self._log_thread.start()

    def stop_log_thread(self):
        """Stop the log worker thread."""
        self._log_running = False
        if self._log_thread:
            self._log_thread.join(timeout=1)
            self._log_thread = None

    def register_log_handler(self, source: str, handler: Callable):
        """Register a log handler for a source."""
        self._log_handlers[source] = handler

    def unregister_log_handler(self, source: str):
        """Remove a log handler for a source."""
        self._log_handlers.pop(source, None)

    def subscribe(self, source: str, callback: Callable):
        """Subscribe to source data."""
        if source not in self._subscribers:
            self._subscribers[source] = []
        if callback not in self._subscribers[source]:
            self._subscribers[source].append(callback)

    def unsubscribe(self, source: str, callback: Callable = None):
        """Unsubscribe one callback or all callbacks for a source."""
        if source in self._subscribers:
            if callback:
                self._subscribers[source] = [
                    cb for cb in self._subscribers[source] if cb != callback
                ]
            else:
                del self._subscribers[source]

    def publish(self, source: str, data: str):
        """Publish source data from an I/O thread without blocking."""
        if not data:
            return

        with self._buffer_lock:
            if source not in self._buffers:
                self._buffers[source] = ""
            self._buffers[source] += data

            if len(self._buffers[source]) > 1024 * 1024:
                self._buffers[source] = self._buffers[source][-512 * 1024:]

        if self._log_queue.qsize() < 10000:
            self._log_queue.put((source, data))

    def _dispatch_batch(self):
        """Flush accumulated source data to UI subscribers."""
        with self._buffer_lock:
            if not self._buffers:
                return
            batch = dict(self._buffers)
            self._buffers.clear()

        for source, data in batch.items():
            if source in self._subscribers:
                for callback in self._subscribers[source]:
                    try:
                        callback(data)
                    except Exception as e:
                        print(f"DataBus dispatch error: {e}")

        if batch:
            self.batch_data_ready.emit(batch)

    def _log_worker(self):
        """Batch log writes on a background thread."""
        log_buffers: Dict[str, List[str]] = {}

        while self._log_running:
            try:
                items = []
                try:
                    while True:
                        item = self._log_queue.get_nowait()
                        items.append(item)
                except queue.Empty:
                    pass

                if not items:
                    import time

                    time.sleep(0.05)
                    continue

                for source, data in items:
                    if source not in log_buffers:
                        log_buffers[source] = []
                    log_buffers[source].append(data)

                for source, data_list in log_buffers.items():
                    if source in self._log_handlers:
                        try:
                            combined = "".join(data_list)
                            self._log_handlers[source](combined)
                        except Exception as e:
                            print(f"Log write error: {e}")

                log_buffers.clear()

            except Exception as e:
                print(f"Log worker error: {e}")


_data_bus: Optional[DataBus] = None


def get_data_bus() -> DataBus:
    """Return the global data bus singleton."""
    global _data_bus
    if _data_bus is None:
        _data_bus = DataBus()
        _data_bus.start_log_thread()
    return _data_bus
