"""
远程日志管理模块
客户端轻量级日志记录（只记录用户操作和关键事件）
"""
import os
from datetime import datetime
from typing import Optional
import threading


class RemoteLogger:
    """
    远程日志记录器

    客户端模式下的轻量级日志：
    - 记录用户发送的命令
    - 记录连接/断开事件
    - 记录错误信息

    不记录完整的串口输出（避免重复保存）
    """

    def __init__(self, remote_port: str, log_dir: str = "logs"):
        self.remote_port = remote_port
        self.log_dir = log_dir
        self._file = None
        self._lock = threading.Lock()
        self._ensure_log_dir()
        self._open_log_file()

    def _ensure_log_dir(self):
        """确保日志目录存在"""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    def _open_log_file(self):
        """打开日志文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_port_name = self.remote_port.replace("/", "_").replace("\\", "_").replace(":", "_")
        filename = f"remote_{safe_port_name}_{timestamp}.log"
        filepath = os.path.join(self.log_dir, filename)
        self._file = open(filepath, "w", encoding="utf-8")
        self._filepath = filepath

    @property
    def filepath(self) -> str:
        """获取日志文件路径"""
        return self._filepath

    def log_command(self, command: str):
        """记录用户发送的命令"""
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        with self._lock:
            if self._file:
                self._file.write(f"{timestamp} [COMMAND] {command}\n")
                self._file.flush()

    def log_event(self, event: str):
        """记录事件"""
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        with self._lock:
            if self._file:
                self._file.write(f"{timestamp} [EVENT] {event}\n")
                self._file.flush()

    def log_error(self, error: str):
        """记录错误"""
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        with self._lock:
            if self._file:
                self._file.write(f"{timestamp} [ERROR] {error}\n")
                self._file.flush()

    def close(self):
        """关闭日志文件"""
        with self._lock:
            if self._file:
                self._file.close()
                self._file = None

    def __del__(self):
        self.close()
