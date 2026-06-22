"""Device state detection based on serial output."""

import re
import threading
import time
from enum import Enum, auto
from typing import Callable, Optional


class PortPhysicalState(Enum):
    """Physical serial port state."""

    CLOSED = auto()
    OPEN = auto()
    NO_DEVICE = auto()
    PERMISSION_ERROR = auto()
    IO_ERROR = auto()


class DeviceRunState(Enum):
    """Runtime state inferred from serial output."""

    UNKNOWN = auto()
    UBOOT = auto()
    KERNEL_BOOTING = auto()
    LOGIN_PROMPT = auto()
    LOGGED_IN = auto()
    KERNEL_PANIC = auto()
    HUNG = auto()
    REBOOTING = auto()


class DeviceStateDetector:
    """Detect device boot/login state from a sliding serial-output window.

    Detection priority:
    1. KERNEL_PANIC   - "Kernel panic" or "Oops:"
    2. REBOOTING      - "Restarting system" or "reboot:"
    3. UBOOT          - "=>" prompt at the end of a recent line
    4. LOGGED_IN      - shell prompt
    5. LOGIN_PROMPT   - "login:" prompt
    6. KERNEL_BOOTING - "Linux version" before login/shell

    HUNG is checked by ``check_hung()`` from an external timer.
    """

    MAX_BUFFER_SIZE = 8192
    TRIM_BUFFER_SIZE = 4096

    def __init__(self, hung_timeout: float = 60.0):
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
        """Set the state-change callback.

        Callback signature:
        ``(old_state: DeviceRunState, new_state: DeviceRunState, detail: str)``.
        """
        self._on_state_change = callback

    def feed(self, data: str):
        """Feed serial text and update the detected state."""
        with self._lock:
            self._last_data_time = time.time()

            self._buffer += data
            if len(self._buffer) > self.MAX_BUFFER_SIZE:
                self._buffer = self._buffer[-self.TRIM_BUFFER_SIZE:]

            self._detect_state()

    def check_hung(self) -> bool:
        """Return True when the detector just entered HUNG state."""
        with self._lock:
            if self._last_data_time <= 0:
                return False

            elapsed = time.time() - self._last_data_time
            if elapsed > self._hung_timeout and self._state not in (
                DeviceRunState.UNKNOWN,
                DeviceRunState.HUNG,
            ):
                self._set_state(
                    DeviceRunState.HUNG,
                    f"No serial output for {elapsed:.0f}s",
                )
                return True
            return False

    def reset(self):
        """Reset state after a serial reconnection."""
        with self._lock:
            self._state = DeviceRunState.UNKNOWN
            self._buffer = ""
            self._last_data_time = 0.0

    def get_full_state(self) -> dict:
        """Return the full state payload for APIs and tooltips."""
        with self._lock:
            return {
                "device_run_state": self._state.name,
                "device_ip": self._device_ip,
                "device_version": self._device_version,
                "last_data_time": self._last_data_time,
                "idle_seconds": (
                    round(time.time() - self._last_data_time, 1)
                    if self._last_data_time > 0
                    else -1
                ),
            }

    def _detect_state(self):
        """Detect state from the recent buffer while holding the lock."""
        recent = self._buffer[-2048:] if len(self._buffer) > 2048 else self._buffer

        if re.search(r"Kernel panic|Oops:", recent):
            self._set_state(DeviceRunState.KERNEL_PANIC, "Detected kernel panic")
            return

        if re.search(r"Restarting system|reboot:\s", recent):
            self._set_state(DeviceRunState.REBOOTING, "Device is rebooting")
            return

        last_lines = recent.split("\n")
        tail = "\n".join(last_lines[-5:]) if len(last_lines) > 5 else recent

        if re.search(r"=>\s*$", tail):
            self._set_state(DeviceRunState.UBOOT, "At U-Boot prompt")
            return

        if re.search(r"\[root@[^\]]+\]#\s*$|root@\S+[#$]\s*$", tail):
            self._set_state(DeviceRunState.LOGGED_IN, "Logged in shell")
            return

        if re.search(r"login:\s*$", tail):
            self._set_state(DeviceRunState.LOGIN_PROMPT, "Waiting for login")
            return

        if re.search(r"Linux version \d", recent):
            self._set_state(DeviceRunState.KERNEL_BOOTING, "Kernel booting")
            return

    def _set_state(self, new_state: DeviceRunState, detail: str = ""):
        """Set a new state while holding the lock."""
        if self._state == new_state:
            return

        old_state = self._state
        self._state = new_state
        self._buffer = ""

        if self._on_state_change:
            callback = self._on_state_change
            threading.Thread(
                target=callback,
                args=(old_state, new_state, detail),
                daemon=True,
            ).start()
