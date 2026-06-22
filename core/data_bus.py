"""
数据总线模块
实现串口/网络数据的异步分发
解耦 I/O 线程、UI 线程、日志线程
"""
import threading
import queue
from typing import Dict, List, Callable, Optional
from dataclasses import dataclass
from enum import Enum, auto
from collections import deque

from PyQt5.QtCore import QObject, pyqtSignal, QTimer


class MessageType(Enum):
    """消息类型"""
    DATA = auto()           # 数据
    STATE_CHANGE = auto()   # 状态变化
    ERROR = auto()          # 错误
    LOG = auto()            # 日志


@dataclass
class Message:
    """消息"""
    msg_type: MessageType
    source: str             # 来源标识（串口名/会话ID）
    data: str               # 数据内容
    timestamp: float = 0    # 时间戳


class DataBus(QObject):
    """
    数据总线 - 核心调度器

    架构:
    [串口线程1] ──┐
    [串口线程2] ──┼──> [消息队列] ──> [UI调度器] ──> [各终端]
    [SSH线程]  ──┘                        │
                                          └──> [日志线程]

    特点:
    - 所有数据通过队列传递，完全异步
    - UI 线程只做分发，不做处理
    - 批量处理，减少信号发射次数
    """

    # 信号：批量数据到达 (source -> data)
    batch_data_ready = pyqtSignal(dict)

    # 单例
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
        # 避免重复初始化
        if DataBus._initialized:
            return
        super().__init__()
        DataBus._initialized = True

        # 消息队列（线程安全）
        self._queue = queue.Queue()

        # 数据缓冲区（按来源分组）
        self._buffers: Dict[str, str] = {}
        self._buffer_lock = threading.Lock()

        # 订阅者
        self._subscribers: Dict[str, List[Callable]] = {}

        # UI 调度定时器（在主线程中批量分发）
        self._dispatch_timer = QTimer()
        self._dispatch_timer.timeout.connect(self._dispatch_batch)
        self._dispatch_timer.start(16)  # 约 60fps

        # 日志队列（独立）
        self._log_queue = queue.Queue()
        self._log_thread: Optional[threading.Thread] = None
        self._log_running = False
        self._log_handlers: Dict[str, Callable] = {}

    def start_log_thread(self):
        """启动日志线程"""
        if self._log_running:
            return
        self._log_running = True
        self._log_thread = threading.Thread(target=self._log_worker, daemon=True)
        self._log_thread.start()

    def stop_log_thread(self):
        """停止日志线程"""
        self._log_running = False
        if self._log_thread:
            self._log_thread.join(timeout=1)
            self._log_thread = None

    def register_log_handler(self, source: str, handler: Callable):
        """注册日志处理器"""
        self._log_handlers[source] = handler

    def unregister_log_handler(self, source: str):
        """注销日志处理器"""
        self._log_handlers.pop(source, None)

    def subscribe(self, source: str, callback: Callable):
        """订阅数据"""
        if source not in self._subscribers:
            self._subscribers[source] = []
        if callback not in self._subscribers[source]:
            self._subscribers[source].append(callback)

    def unsubscribe(self, source: str, callback: Callable = None):
        """取消订阅"""
        if source in self._subscribers:
            if callback:
                self._subscribers[source] = [
                    cb for cb in self._subscribers[source] if cb != callback
                ]
            else:
                del self._subscribers[source]

    def publish(self, source: str, data: str):
        """
        发布数据（从 I/O 线程调用）
        线程安全，不阻塞
        """
        if not data:
            return

        # 放入缓冲区（按来源分组）
        with self._buffer_lock:
            if source not in self._buffers:
                self._buffers[source] = ""
            self._buffers[source] += data

            # 限制单个缓冲区大小，防止内存泄漏
            if len(self._buffers[source]) > 1024 * 1024:  # 1MB
                self._buffers[source] = self._buffers[source][-512 * 1024:]  # 保留最后 512KB

        # 同时放入日志队列（限制队列大小）
        if self._log_queue.qsize() < 10000:
            self._log_queue.put((source, data))

    def _dispatch_batch(self):
        """
        批量分发数据到 UI（在主线程中执行）
        每 16ms 执行一次，合并所有累积的数据
        """
        # 获取并清空缓冲区
        with self._buffer_lock:
            if not self._buffers:
                return
            batch = dict(self._buffers)
            self._buffers.clear()

        # 分发给订阅者
        for source, data in batch.items():
            if source in self._subscribers:
                for callback in self._subscribers[source]:
                    try:
                        callback(data)
                    except Exception as e:
                        print(f"DataBus dispatch error: {e}")

        # 发射批量信号（备用）
        if batch:
            self.batch_data_ready.emit(batch)

    def _log_worker(self):
        """日志工作线程"""
        # 批量写入缓冲
        log_buffers: Dict[str, List[str]] = {}

        while self._log_running:
            try:
                # 批量获取日志
                items = []
                try:
                    while True:
                        item = self._log_queue.get_nowait()
                        items.append(item)
                except queue.Empty:
                    pass

                if not items:
                    # 没有数据，短暂休眠
                    import time
                    time.sleep(0.05)
                    continue

                # 按来源分组
                for source, data in items:
                    if source not in log_buffers:
                        log_buffers[source] = []
                    log_buffers[source].append(data)

                # 批量写入
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


# 全局数据总线实例
_data_bus: Optional[DataBus] = None


def get_data_bus() -> DataBus:
    """获取数据总线单例"""
    global _data_bus
    if _data_bus is None:
        _data_bus = DataBus()
        _data_bus.start_log_thread()
    return _data_bus
