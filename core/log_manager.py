"""
日志管理模块
负责日志文件的命名、清理、轮转
"""
import os
import time
import threading
from datetime import datetime, timedelta
from typing import Optional


class LogManager:
    """
    日志生命周期管理器

    功能:
    - 根据命名模板生成日志文件名
    - 自动清理过期日志（按天数、总大小）
    - 清理空日志文件
    - 单文件大小轮转
    """

    def __init__(self, log_dir: str, name_pattern: str = "{port}_{date}_{time}",
                 max_days: int = 30, max_total_size_mb: int = 500,
                 max_file_size_mb: int = 50, auto_clean: bool = True):
        self.log_dir = log_dir
        self.name_pattern = name_pattern
        self.max_days = max_days
        self.max_total_size_mb = max_total_size_mb
        self.max_file_size_mb = max_file_size_mb
        self.auto_clean = auto_clean
        self._lock = threading.Lock()

    def generate_filename(self, port_name: str, port_alias: str = "") -> str:
        """
        根据命名模板生成日志文件名

        支持变量:
        - {port}  端口名（如 COM3、ttyUSB0）
        - {date}  日期 YYYYMMDD
        - {time}  时间 HHMMSS
        - {name}  端口别名（无则同 port）
        """
        now = datetime.now()
        safe_port = port_name.replace("/", "_").replace("\\", "_").replace(":", "_")
        safe_alias = (port_alias or safe_port).replace("/", "_").replace("\\", "_").replace(":", "_")

        filename = self.name_pattern.format(
            port=safe_port,
            date=now.strftime("%Y%m%d"),
            time=now.strftime("%H%M%S"),
            name=safe_alias,
        )
        # 确保以 .log 结尾
        if not filename.endswith(".log"):
            filename += ".log"
        return filename

    # ---- 清理 ----

    def cleanup(self):
        """执行一次完整清理（线程安全）"""
        if not self.auto_clean:
            return
        with self._lock:
            self._clean_empty_files()
            self._clean_by_days()
            self._clean_by_total_size()

    def cleanup_async(self):
        """在后台线程执行清理"""
        t = threading.Thread(target=self.cleanup, daemon=True)
        t.start()

    def get_stats(self) -> dict:
        """获取日志目录统计信息"""
        total_size = 0
        file_count = 0
        if os.path.isdir(self.log_dir):
            for f in os.listdir(self.log_dir):
                fp = os.path.join(self.log_dir, f)
                if os.path.isfile(fp) and f.endswith(".log"):
                    total_size += os.path.getsize(fp)
                    file_count += 1
        return {
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "file_count": file_count,
        }

    def force_cleanup(self):
        """强制清理（忽略 auto_clean 开关）"""
        with self._lock:
            self._clean_empty_files()
            self._clean_by_days()
            self._clean_by_total_size()

    def _log_files_sorted(self):
        """获取日志文件列表，按修改时间从旧到新排序"""
        if not os.path.isdir(self.log_dir):
            return []
        files = []
        for f in os.listdir(self.log_dir):
            fp = os.path.join(self.log_dir, f)
            if os.path.isfile(fp) and f.endswith(".log"):
                files.append(fp)
        files.sort(key=lambda p: os.path.getmtime(p))
        return files

    def _clean_empty_files(self):
        """删除超过 1 小时未修改的 0 字节日志文件"""
        threshold = time.time() - 3600
        for fp in self._log_files_sorted():
            try:
                if os.path.getsize(fp) == 0 and os.path.getmtime(fp) < threshold:
                    os.remove(fp)
            except OSError:
                pass

    def _clean_by_days(self):
        """删除超过保留天数的日志文件"""
        if self.max_days <= 0:
            return
        cutoff = time.time() - self.max_days * 86400
        for fp in self._log_files_sorted():
            try:
                if os.path.getmtime(fp) < cutoff:
                    os.remove(fp)
            except OSError:
                pass

    def _clean_by_total_size(self):
        """总大小超限时从最旧的文件开始删除"""
        if self.max_total_size_mb <= 0:
            return
        max_bytes = self.max_total_size_mb * 1024 * 1024
        files = self._log_files_sorted()
        total = sum(os.path.getsize(fp) for fp in files if os.path.exists(fp))
        for fp in files:
            if total <= max_bytes:
                break
            try:
                size = os.path.getsize(fp)
                os.remove(fp)
                total -= size
            except OSError:
                pass

    # ---- 轮转 ----

    def check_rotation(self, filepath: str) -> Optional[str]:
        """
        检查文件是否需要轮转。
        如果需要，返回新的文件路径；否则返回 None。
        """
        if self.max_file_size_mb <= 0:
            return None
        try:
            if os.path.getsize(filepath) < self.max_file_size_mb * 1024 * 1024:
                return None
        except OSError:
            return None

        # 生成轮转文件名: xxx.log -> xxx_1.log, xxx_1.log -> xxx_2.log ...
        base, ext = os.path.splitext(filepath)
        idx = 1
        while True:
            new_path = f"{base}_{idx}{ext}"
            if not os.path.exists(new_path):
                return new_path
            idx += 1
