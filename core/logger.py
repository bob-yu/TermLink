"""
日志记录模块
负责串口日志的记录，支持命名模板和文件轮转
"""
import os
import re
from datetime import datetime
from typing import Optional
import threading

from .log_manager import LogManager

# ANSI 转义序列正则表达式
ANSI_ESCAPE_PATTERN = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]|\x1b\].*?\x07|\x1b[()][AB012]|\x1b[>=]')


class SerialLogger:
    """
    串口日志记录器

    功能:
    - 按端口区分日志文件
    - 带时间戳记录
    - 线程安全
    - 支持启用/禁用
    - 支持命名模板（通过 LogManager）
    - 支持单文件大小轮转（通过 LogManager）
    """

    def __init__(self, port_name: str, log_dir: str = "logs",
                 enabled: bool = True, add_timestamp: bool = True,
                 log_manager: Optional[LogManager] = None,
                 port_alias: str = ""):
        self.port_name = port_name
        self.log_dir = log_dir
        self._file = None
        self._lock = threading.Lock()
        self._enabled = enabled
        self._add_timestamp = add_timestamp
        self._filepath = ""
        self._log_manager = log_manager
        self._port_alias = port_alias
        self._write_count = 0  # 写入计数，用于定期检查轮转

        if self._enabled:
            self._ensure_log_dir()
            self._open_log_file()

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        with self._lock:
            if value and not self._enabled:
                self._enabled = True
                self._ensure_log_dir()
                self._open_log_file()
            elif not value and self._enabled:
                self._enabled = False
                if self._file:
                    self._file.close()
                    self._file = None

    def _ensure_log_dir(self):
        """确保日志目录存在"""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir, exist_ok=True)

    def _open_log_file(self):
        """打开日志文件"""
        if self._log_manager:
            filename = self._log_manager.generate_filename(
                self.port_name, self._port_alias
            )
        else:
            # 兼容：无 LogManager 时使用默认命名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_port = self.port_name.replace("/", "_").replace("\\", "_").replace(":", "_")
            filename = f"{safe_port}_{timestamp}.log"

        filepath = os.path.join(self.log_dir, filename)
        self._file = open(filepath, "w", encoding="utf-8")
        self._filepath = filepath

    @property
    def filepath(self) -> str:
        """获取日志文件路径"""
        return self._filepath

    def write(self, data: str, add_timestamp: bool = None):
        """
        写入日志

        Args:
            data: 要写入的数据
            add_timestamp: 是否添加时间戳（None 表示使用默认设置）
        """
        if not self._enabled:
            return

        if add_timestamp is None:
            add_timestamp = self._add_timestamp

        with self._lock:
            if self._file is None:
                return

            if add_timestamp:
                clean_data = ANSI_ESCAPE_PATTERN.sub('', data)
                normalized_data = clean_data.replace('\r\n', '\n').replace('\r', '\n')
                lines = normalized_data.split('\n')
                for line in lines:
                    line = line.rstrip()
                    if line:
                        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S.%f")[:-3] + "]"
                        self._file.write(f"{timestamp} {line}\n")
            else:
                self._file.write(data)

            self._file.flush()

            # 每 100 次写入检查一次轮转
            self._write_count += 1
            if self._write_count >= 100:
                self._write_count = 0
                self._check_rotation()

    def _check_rotation(self):
        """检查是否需要文件轮转（在 _lock 内调用）"""
        if not self._log_manager or not self._filepath:
            return
        new_path = self._log_manager.check_rotation(self._filepath)
        if new_path:
            if self._file:
                self._file.close()
            self._file = open(new_path, "w", encoding="utf-8")
            self._filepath = new_path

    def write_raw(self, data: str):
        """写入原始数据（不添加时间戳）"""
        self.write(data, add_timestamp=False)

    def write_event(self, event: str):
        """写入事件日志"""
        if not self._enabled:
            return
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        with self._lock:
            if self._file:
                self._file.write(f"{timestamp} [EVENT] {event}\n")
                self._file.flush()

    def close(self):
        """关闭日志文件"""
        with self._lock:
            if self._file:
                self._file.close()
                self._file = None

    def __del__(self):
        self.close()
