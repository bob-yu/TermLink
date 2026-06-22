"""
设备状态精确检测模块

通过分析串口输出内容，判断设备当前处于什么阶段。
分离两层状态：串口物理状态 + 设备运行状态。

串口物理状态 (PortPhysicalState):
    关注 USB 线是否连接、串口是否能打开、是否有权限

设备运行状态 (DeviceRunState):
    关注设备当前处于启动的哪个阶段（U-Boot / 内核启动 / 登录 / shell 等）
    通过分析串口输出内容（模式匹配）判断
"""

import re
import time
import threading
from enum import Enum, auto
from typing import Optional, Callable


class PortPhysicalState(Enum):
    """串口物理层状态"""
    CLOSED = auto()           # 串口未打开
    OPEN = auto()             # 串口已打开，可以收发数据
    NO_DEVICE = auto()        # 串口设备不存在（USB 拔出）
    PERMISSION_ERROR = auto() # 无权限访问
    IO_ERROR = auto()         # I/O 错误（硬件故障）


class DeviceRunState(Enum):
    """设备运行状态（通过串口输出内容判断）"""
    UNKNOWN = auto()          # 未知（刚连接，还没收到数据）
    UBOOT = auto()            # 在 U-Boot 命令行
    KERNEL_BOOTING = auto()   # 内核启动中
    LOGIN_PROMPT = auto()     # 在 login 提示符（系统启动完成，未登录）
    LOGGED_IN = auto()        # 已登录（在 shell 中）
    KERNEL_PANIC = auto()     # 内核 panic
    HUNG = auto()             # 疑似死机（长时间无输出）
    REBOOTING = auto()        # 正在重启


class DeviceStateDetector:
    """
    设备状态检测器

    持续分析串口输出，维护设备当前状态。
    使用滑动窗口缓冲区 + 模式匹配。

    检测优先级（从高到低）:
    1. KERNEL_PANIC  — "Kernel panic" / "Oops:"
    2. REBOOTING     — "Restarting system" / "reboot:"
    3. UBOOT         — "=>" 出现在行尾
    4. KERNEL_BOOTING — "Linux version" 且还没到 login
    5. LOGIN_PROMPT  — "login:" 出现在行尾
    6. LOGGED_IN     — "[root@xxx]#" 出现在行尾

    HUNG 状态由外部定时器触发（check_hung），不在 feed() 中判断。
    """

    # 缓冲区最大大小
    MAX_BUFFER_SIZE = 8192
    # 缓冲区裁剪后保留大小
    TRIM_BUFFER_SIZE = 4096

    def __init__(self, hung_timeout: float = 60.0):
        """
        Args:
            hung_timeout: 无串口输出超过此时间（秒）判定为 HUNG
        """
        self._state = DeviceRunState.UNKNOWN
        self._buffer = ""
        self._last_data_time: float = 0.0
        self._hung_timeout = hung_timeout
        self._device_ip = ""
        self._device_version = ""
        self._on_state_change: Optional[Callable] = None
        self._lock = threading.Lock()

    @property
    def state(self) -> DeviceRunState:
        with self._lock:
            return self._state

    @property
    def device_ip(self) -> str:
        return self._device_ip

    @device_ip.setter
    def device_ip(self, value: str):
        self._device_ip = value

    @property
    def device_version(self) -> str:
        return self._device_version

    @device_version.setter
    def device_version(self, value: str):
        self._device_version = value

    def set_state_change_callback(self, callback: Callable):
        """
        设置状态变化回调。

        callback 签名: (old_state: DeviceRunState, new_state: DeviceRunState, detail: str) -> None
        """
        self._on_state_change = callback

    def feed(self, data: str):
        """
        喂入串口数据，更新状态。

        Args:
            data: 串口收到的文本数据
        """
        with self._lock:
            self._last_data_time = time.time()

            # 追加到缓冲区（滑动窗口）
            self._buffer += data
            if len(self._buffer) > self.MAX_BUFFER_SIZE:
                self._buffer = self._buffer[-self.TRIM_BUFFER_SIZE:]

            # 如果之前是 HUNG，收到数据说明恢复了，先清除 HUNG 状态
            if self._state == DeviceRunState.HUNG:
                # 不直接设置状态，让下面的检测逻辑判断当前应该是什么状态
                pass

            # 状态检测
            self._detect_state()

    def check_hung(self) -> bool:
        """
        检查是否疑似死机（由外部定时器调用，建议每 10 秒一次）。

        Returns:
            True 如果刚刚进入 HUNG 状态
        """
        with self._lock:
            if self._last_data_time <= 0:
                return False

            elapsed = time.time() - self._last_data_time
            if elapsed > self._hung_timeout and self._state not in (
                DeviceRunState.UNKNOWN, DeviceRunState.HUNG
            ):
                self._set_state(
                    DeviceRunState.HUNG,
                    f"无串口输出超过 {elapsed:.0f}s"
                )
                return True
            return False

    def reset(self):
        """重置状态（串口重新连接时调用）"""
        with self._lock:
            self._state = DeviceRunState.UNKNOWN
            self._buffer = ""
            self._last_data_time = 0.0

    def get_full_state(self) -> dict:
        """获取完整状态信息（供 API 返回）"""
        with self._lock:
            return {
                "device_run_state": self._state.name,
                "device_ip": self._device_ip,
                "device_version": self._device_version,
                "last_data_time": self._last_data_time,
                "idle_seconds": round(time.time() - self._last_data_time, 1) if self._last_data_time > 0 else -1,
            }

    def _detect_state(self):
        """分析缓冲区内容，判断设备状态（在锁内调用）"""
        buf = self._buffer

        # 只分析最近的内容（避免历史数据干扰）
        # 取最后 2KB 用于检测
        recent = buf[-2048:] if len(buf) > 2048 else buf

        # 1. Kernel panic（最高优先级）
        if re.search(r'Kernel panic|Oops:', recent):
            self._set_state(DeviceRunState.KERNEL_PANIC, "检测到内核 panic")
            return

        # 2. 正在重启
        if re.search(r'Restarting system|reboot:\s', recent):
            self._set_state(DeviceRunState.REBOOTING, "设备正在重启")
            return

        # 3. U-Boot（检查最近几行）
        last_lines = recent.split('\n')
        tail = '\n'.join(last_lines[-5:]) if len(last_lines) > 5 else recent
        if re.search(r'=>\s*$', tail):
            self._set_state(DeviceRunState.UBOOT, "在 U-Boot 命令行")
            return

        # 4. 已登录（shell 提示符）— 优先于 login prompt 检测
        if re.search(r'\[root@[^\]]+\]#\s*$|root@\S+[#$]\s*$', tail):
            self._set_state(DeviceRunState.LOGGED_IN, "已登录 shell")
            return

        # 5. Login 提示符
        if re.search(r'login:\s*$', tail):
            self._set_state(DeviceRunState.LOGIN_PROMPT, "等待登录")
            return

        # 6. 内核启动中（看到 Linux version 但还没到 login/shell）
        if re.search(r'Linux version \d', recent):
            self._set_state(DeviceRunState.KERNEL_BOOTING, "内核启动中")
            return

    def _set_state(self, new_state: DeviceRunState, detail: str = ""):
        """设置新状态（在锁内调用）"""
        if self._state != new_state:
            old_state = self._state
            self._state = new_state
            # 状态变化时清空缓冲区，避免旧数据干扰下次判断
            self._buffer = ""
            if self._on_state_change:
                # 回调在锁外执行，避免死锁
                # 但这里我们在锁内，所以用线程执行
                callback = self._on_state_change
                threading.Thread(
                    target=callback,
                    args=(old_state, new_state, detail),
                    daemon=True
                ).start()
