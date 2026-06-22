import queue
import threading
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional

import serial
import serial.tools.list_ports
from PyQt5.QtCore import QObject, pyqtSignal

from .data_bus import get_data_bus
from .device_info_parser import parse_ip_from_ifconfig, parse_version_from_command_output
from .device_state import DeviceRunState, DeviceStateDetector
from .logger import SerialLogger
from .login_state_machine import LoginConfig, LoginState, LoginStateMachine


class WorkerState(Enum):
    STOPPED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    DISCONNECTED = auto()
    ERROR = auto()


@dataclass
class SerialConfig:
    port: str
    baudrate: int = 115200
    bytesize: int = 8
    parity: str = "N"
    stopbits: float = 1
    flow_control: str = "none"
    timeout: float = 0.05
    name: str = ""

    def __post_init__(self):
        if not self.name:
            self.name = self.port


class SerialWorker(QObject):
    state_changed = pyqtSignal(WorkerState)
    login_state_changed = pyqtSignal(LoginState)
    error_occurred = pyqtSignal(str)
    keyword_detected = pyqtSignal(str, str)
    device_info_received = pyqtSignal(str, str)
    device_state_changed = pyqtSignal(str, str, str)
    data_received = pyqtSignal(str)

    def __init__(
        self,
        config: SerialConfig,
        log_dir: str = "logs",
        log_enabled: bool = True,
        log_timestamp: bool = True,
        log_manager=None,
    ):
        super().__init__()
        self.config = config
        self._serial: Optional[serial.Serial] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._write_queue = queue.Queue()
        self._state = WorkerState.STOPPED

        self._data_bus = get_data_bus()
        self._source_id = config.port
        self._logger = SerialLogger(
            config.name or config.port,
            log_dir,
            enabled=log_enabled,
            add_timestamp=log_timestamp,
            log_manager=log_manager,
            port_alias=config.name or "",
        )
        if log_enabled:
            self._data_bus.register_log_handler(
                self._source_id,
                lambda data: self._logger.write(data),
            )

        self._login_machine: Optional[LoginStateMachine] = None
        self._auto_login_enabled = False
        self._auto_commands: List[str] = []
        self._keywords: Dict[str, List[str]] = {}
        self._auto_reconnect = False
        self._reconnect_interval = 5
        self._error_count = 0
        self._last_error_time = 0

        self._info_capture_enabled = False
        self._info_capture_type = ""
        self._info_buffer = ""
        self._device_version = ""
        self._device_ip = ""
        self._login_prompt_buffer = ""

        self._device_state = DeviceStateDetector(hung_timeout=60.0)
        self._device_state.set_state_change_callback(self._on_device_state_change)

    @property
    def state(self) -> WorkerState:
        return self._state

    @state.setter
    def state(self, new_state: WorkerState):
        if self._state != new_state:
            self._state = new_state
            self.state_changed.emit(new_state)

    @property
    def is_connected(self) -> bool:
        return self._state == WorkerState.CONNECTED

    @property
    def log_filepath(self) -> str:
        return self._logger.filepath

    @property
    def source_id(self) -> str:
        return self._source_id

    def setup_login(self, login_config: LoginConfig):
        self._login_machine = LoginStateMachine(login_config)
        self._login_machine.set_send_callback(self._send_login_data)
        self._login_machine.set_state_change_callback(self._on_login_state_change)
        self._auto_login_enabled = False

    def set_auto_commands(self, commands: List[str]):
        self._auto_commands = commands.copy()

    def set_keywords(self, keywords: Dict[str, List[str]]):
        self._keywords = keywords.copy()

    def set_auto_reconnect(self, enabled: bool, interval: float = 5):
        self._auto_reconnect = enabled
        self._reconnect_interval = interval

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        self._close_serial()
        self._logger.close()
        self._data_bus.unregister_log_handler(self._source_id)
        self.state = WorkerState.STOPPED

    def write(self, data: str):
        if self._write_queue.qsize() >= 1000:
            try:
                self._write_queue.get_nowait()
            except queue.Empty:
                pass
        self._write_queue.put(data)

    def send_command(self, command: str):
        if not command.endswith("\n"):
            command += "\n"
        self.write(command)

    def send_break(self):
        if self._serial and self._serial.is_open:
            try:
                self._serial.send_break(duration=0.25)
            except Exception as exc:
                self.error_occurred.emit(f"Send break failed: {exc}")

    def start_login(self):
        if self._login_machine:
            self._auto_login_enabled = True
            self._login_machine.start()

    def _run(self):
        while self._running:
            try:
                if not self._serial or not self._serial.is_open:
                    self._connect()
                    if not self._serial:
                        if self._auto_reconnect:
                            time.sleep(self._reconnect_interval)
                            continue
                        break

                self._read_data()
                self._process_write_queue()
            except serial.SerialException as exc:
                self.error_occurred.emit(str(exc))
                self.state = WorkerState.DISCONNECTED
                self._close_serial()
                if self._auto_reconnect:
                    time.sleep(self._reconnect_interval)
                else:
                    break
            except Exception as exc:
                current_time = time.time()
                if current_time - self._last_error_time > 5:
                    self._error_count = 0
                self._error_count += 1
                self._last_error_time = current_time
                if self._error_count <= 3:
                    self.error_occurred.emit(str(exc))
                elif self._error_count == 4:
                    self.error_occurred.emit("Too many serial worker errors; suppressing repeats.")
                time.sleep(min(0.1 * self._error_count, 2.0))

    def _connect(self):
        self.state = WorkerState.CONNECTING
        try:
            self._serial = serial.Serial(
                port=self.config.port,
                baudrate=self.config.baudrate,
                bytesize=self.config.bytesize,
                parity=self.config.parity,
                stopbits=self.config.stopbits,
                xonxoff=self.config.flow_control == "xonxoff",
                rtscts=self.config.flow_control == "rtscts",
                dsrdtr=self.config.flow_control == "dsrdtr",
                timeout=self.config.timeout,
            )
            self.state = WorkerState.CONNECTED
            if self._auto_login_enabled and self._login_machine:
                self._login_machine.start()
        except serial.SerialException as exc:
            self.error_occurred.emit(f"Connection failed: {exc}")
            self.state = WorkerState.ERROR
            self._serial = None

    def _close_serial(self):
        if self._serial:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None

    def _read_data(self):
        if not self._serial or not self._serial.is_open:
            return
        try:
            data = self._serial.read(1)
            if not data:
                return
            remaining = self._serial.in_waiting
            if remaining > 0:
                data += self._serial.read(remaining)
            text = data.decode("utf-8", errors="replace")
            self._data_bus.publish(self._source_id, text)
            self.data_received.emit(text)
            self._process_internal(text)
        except Exception as exc:
            self.error_occurred.emit(f"Read failed: {exc}")

    def _process_internal(self, text: str):
        if self._auto_login_enabled and self._login_machine:
            self._login_machine.feed(text)
        self._check_keywords(text)
        self._process_info_capture(text)
        self._check_login_prompt(text)
        self._device_state.feed(text)

    def _check_login_prompt(self, text: str):
        self._login_prompt_buffer += text
        if len(self._login_prompt_buffer) > 500:
            self._login_prompt_buffer = self._login_prompt_buffer[-500:]
        # Keep the buffer for state detection only. Do not auto-login or auto-probe.

    def _process_write_queue(self):
        try:
            while not self._write_queue.empty():
                data = self._write_queue.get_nowait()
                if self._serial and self._serial.is_open:
                    if isinstance(data, str):
                        data = data.encode("utf-8")
                    self._serial.write(data)
                    self._serial.flush()
        except queue.Empty:
            pass
        except Exception as exc:
            self.error_occurred.emit(f"Write failed: {exc}")

    def _send_login_data(self, data: str):
        self.write(data)

    def _on_login_state_change(self, state: LoginState):
        self.login_state_changed.emit(state)
        if state == LoginState.READY:
            self._execute_auto_commands()

    def _execute_auto_commands(self):
        for cmd in self._auto_commands:
            self.send_command(cmd)
            time.sleep(0.3)

    def _check_keywords(self, text: str):
        for keyword_type, keywords in self._keywords.items():
            for keyword in keywords:
                if keyword in text:
                    for line in text.split("\n"):
                        if keyword in line:
                            self.keyword_detected.emit(keyword_type, line.strip())

    def is_logged_in(self) -> bool:
        return bool(self._login_machine and self._login_machine.state == LoginState.READY)

    def request_device_info(self):
        if not self.is_connected or not self.is_logged_in():
            return
        self.fetch_device_info()

    def fetch_device_info(self):
        if not self.is_connected:
            return
        self._device_version = ""

        def delayed_get_info():
            time.sleep(0.2)
            if self.is_connected:
                self._start_info_capture("version")
                self.send_command("cat /system/bin/version")

        threading.Thread(target=delayed_get_info, daemon=True).start()

    def login_and_get_device_info(self):
        self.request_device_info()

    def _start_info_capture(self, info_type: str):
        self._info_capture_enabled = True
        self._info_capture_type = info_type
        self._info_buffer = ""

    def _process_info_capture(self, text: str):
        if not self._info_capture_enabled:
            return
        self._info_buffer += text
        if len(self._info_buffer) > 4096:
            self._info_buffer = self._info_buffer[-4096:]
        if "[root@" not in self._info_buffer or "]#" not in self._info_buffer:
            return

        self._info_capture_enabled = False
        if self._info_capture_type == "version":
            self._device_version = parse_version_from_command_output(self._info_buffer)
            self._info_buffer = ""
            self._start_info_capture("ip")
            self.send_command(
                "ifconfig eth0 2>/dev/null | grep -E 'inet |inet addr' || "
                "ifconfig 2>/dev/null | grep -E 'inet |inet addr' | head -1"
            )
            return

        if self._info_capture_type == "ip":
            ip = parse_ip_from_ifconfig(self._info_buffer)
            if ip:
                self._device_ip = ip
            self._info_buffer = ""
            self.device_info_received.emit(self._device_version, self._device_ip)

    @staticmethod
    def list_ports() -> List[str]:
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]

    @staticmethod
    def list_port_labels() -> Dict[str, str]:
        labels = {}
        for port in serial.tools.list_ports.comports():
            parts = [port.device]
            details = []
            if port.description and port.description != port.device:
                details.append(port.description)
            if port.hwid:
                details.append(port.hwid)
            if details:
                parts.append(" - " + " | ".join(details))
            labels[port.device] = "".join(parts)
        return labels

    @property
    def device_run_state(self) -> DeviceRunState:
        return self._device_state.state

    def get_full_device_state(self) -> dict:
        state = self._device_state.get_full_state()
        state["physical_state"] = self._state.name
        if self._device_ip:
            state["device_ip"] = self._device_ip
        if self._device_version:
            state["device_version"] = self._device_version
        return state

    def _on_device_state_change(
        self,
        old_state: DeviceRunState,
        new_state: DeviceRunState,
        detail: str,
    ):
        self.device_state_changed.emit(old_state.name, new_state.name, detail)
