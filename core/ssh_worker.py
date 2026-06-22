"""
SSH/Telnet 工作模块
支持 SSH 和 Telnet 连接，提供与 SerialWorker 相同的接口
使用 DataBus 实现高性能异步数据分发
"""
import threading
import time
import socket
from typing import Optional, List, Dict, Callable
from dataclasses import dataclass
from enum import Enum, auto

from PyQt5.QtCore import QObject, pyqtSignal

from .data_bus import get_data_bus
from .logger import SerialLogger
from .simple_telnet import SimpleTelnet

try:
    import paramiko
    HAS_PARAMIKO = True
except ImportError:
    HAS_PARAMIKO = False

try:
    import telnetlib
    HAS_TELNETLIB = True
except ImportError:
    # Python 3.13+ 移除了 telnetlib
    HAS_TELNETLIB = False




class ConnectionType(Enum):
    """连接类型"""
    SSH = auto()
    TELNET = auto()


class WorkerState(Enum):
    """工作状态"""
    STOPPED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    DISCONNECTED = auto()
    ERROR = auto()


@dataclass
class SSHConfig:
    """SSH 配置"""
    host: str
    port: int = 22
    username: str = "root"
    password: str = ""
    key_file: str = ""  # 私钥文件路径
    name: str = ""
    connection_type: ConnectionType = ConnectionType.SSH


@dataclass
class TelnetConfig:
    """Telnet 配置"""
    host: str
    port: int = 23
    username: str = ""
    password: str = ""
    name: str = ""
    connection_type: ConnectionType = ConnectionType.TELNET


class SSHWorker(QObject):
    """
    SSH 工作线程
    提供与 SerialWorker 相同的接口
    使用 DataBus 进行高性能数据分发
    """

    # Qt 信号（保留兼容性）
    data_received = pyqtSignal(str)
    state_changed = pyqtSignal(WorkerState)
    error_occurred = pyqtSignal(str)

    def __init__(self, config: SSHConfig, log_dir: str = "logs", log_enabled: bool = True, log_timestamp: bool = True):
        super().__init__()
        self.config = config
        self._log_dir = log_dir

        self._state = WorkerState.STOPPED
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # SSH 相关
        self._client: Optional[paramiko.SSHClient] = None
        self._channel: Optional[paramiko.Channel] = None

        # 日志配置
        self._log_enabled = log_enabled
        self._log_timestamp = log_timestamp

        # 数据总线
        self._data_bus = get_data_bus()
        self._source_id = f"ssh://{config.host}:{config.port}"

        # 日志记录器
        self._logger = SerialLogger(
            config.name or f"ssh_{config.host}",
            log_dir,
            enabled=log_enabled,
            add_timestamp=log_timestamp
        )

        # 注册日志处理器
        if log_enabled:
            self._data_bus.register_log_handler(
                self._source_id,
                lambda data: self._logger.write(data)
            )

        # 自动重连
        self._auto_reconnect = False
        self._reconnect_interval = 5

    @property
    def state(self) -> WorkerState:
        return self._state

    @property
    def is_connected(self) -> bool:
        return self._state == WorkerState.CONNECTED

    @property
    def log_filepath(self) -> str:
        return self._logger.filepath

    @property
    def source_id(self) -> str:
        return self._source_id

    def set_auto_reconnect(self, enabled: bool, interval: float = 5):
        """设置自动重连"""
        self._auto_reconnect = enabled
        self._reconnect_interval = interval

    def start(self):
        """启动连接"""
        if self._running:
            return

        if not HAS_PARAMIKO:
            self.error_occurred.emit("未安装 paramiko 库，请运行: pip install paramiko")
            return

        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """停止连接"""
        self._running = False
        self._close_connection()

        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

        self._logger.close()
        self._data_bus.unregister_log_handler(self._source_id)
        self._set_state(WorkerState.STOPPED)

    def write(self, data: str):
        """发送数据"""
        if self._channel and self._state == WorkerState.CONNECTED:
            try:
                self._channel.send(data)
            except Exception as e:
                self.error_occurred.emit(f"发送失败: {e}")

    def send_command(self, command: str):
        """发送命令（自动添加换行）"""
        if not command.endswith('\n'):
            command += '\n'
        self.write(command)

    def _run(self):
        """工作线程主循环"""
        while self._running:
            try:
                self._connect()
                self._receive_loop()
            except Exception as e:
                self.error_occurred.emit(f"连接错误: {e}")
                self._set_state(WorkerState.ERROR)

            self._close_connection()

            if self._running and self._auto_reconnect:
                self._set_state(WorkerState.DISCONNECTED)
                time.sleep(self._reconnect_interval)
            else:
                break

    def _connect(self):
        """建立 SSH 连接"""
        self._set_state(WorkerState.CONNECTING)

        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # 连接参数
        connect_kwargs = {
            'hostname': self.config.host,
            'port': self.config.port,
            'username': self.config.username,
            'timeout': 10,
            'allow_agent': False,
            'look_for_keys': False,
        }

        # 密钥或密码认证
        if self.config.key_file:
            connect_kwargs['key_filename'] = self.config.key_file
        else:
            connect_kwargs['password'] = self.config.password

        self._client.connect(**connect_kwargs)

        # 获取交互式 shell
        self._channel = self._client.invoke_shell(
            term='xterm-256color',
            width=120,
            height=40
        )
        self._channel.settimeout(0.1)

        self._set_state(WorkerState.CONNECTED)

    def _receive_loop(self):
        """接收数据循环"""
        while self._running and self._channel:
            try:
                if self._channel.recv_ready():
                    data = self._channel.recv(4096)
                    if data:
                        text = data.decode('utf-8', errors='replace')
                        # 通过 DataBus 发布（异步，不阻塞）
                        self._data_bus.publish(self._source_id, text)
                        # 同时发信号（兼容旧代码）
                        self.data_received.emit(text)
                    else:
                        # 连接关闭
                        break
                else:
                    time.sleep(0.001)  # 短暂休眠避免 CPU 空转

            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    self.error_occurred.emit(f"接收错误: {e}")
                break

    def _close_connection(self):
        """关闭连接"""
        if self._channel:
            try:
                self._channel.close()
            except:
                pass
            self._channel = None

        if self._client:
            try:
                self._client.close()
            except:
                pass
            self._client = None

    def _set_state(self, state: WorkerState):
        """设置状态"""
        if self._state != state:
            self._state = state
            self.state_changed.emit(state)

    @staticmethod
    def is_available() -> bool:
        """检查 SSH 功能是否可用"""
        return HAS_PARAMIKO


class TelnetWorker(QObject):
    """
    Telnet 工作线程
    提供与 SerialWorker 相同的接口
    使用 DataBus 进行高性能数据分发
    支持 Python 3.13+（使用 SimpleTelnet 替代 telnetlib）
    """

    # Qt 信号（保留兼容性）
    data_received = pyqtSignal(str)
    state_changed = pyqtSignal(WorkerState)
    error_occurred = pyqtSignal(str)

    def __init__(self, config: TelnetConfig, log_dir: str = "logs", log_enabled: bool = True, log_timestamp: bool = True):
        super().__init__()
        self.config = config
        self._log_dir = log_dir

        self._state = WorkerState.STOPPED
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Telnet 相关（兼容 telnetlib 和 SimpleTelnet）
        self._tn = None

        # 日志配置
        self._log_enabled = log_enabled
        self._log_timestamp = log_timestamp

        # 数据总线
        self._data_bus = get_data_bus()
        self._source_id = f"telnet://{config.host}:{config.port}"

        # 日志记录器
        self._logger = SerialLogger(
            config.name or f"telnet_{config.host}",
            log_dir,
            enabled=log_enabled,
            add_timestamp=log_timestamp
        )

        # 注册日志处理器
        if log_enabled:
            self._data_bus.register_log_handler(
                self._source_id,
                lambda data: self._logger.write(data)
            )

        # 自动重连
        self._auto_reconnect = False
        self._reconnect_interval = 5

    @property
    def state(self) -> WorkerState:
        return self._state

    @property
    def is_connected(self) -> bool:
        return self._state == WorkerState.CONNECTED

    @property
    def log_filepath(self) -> str:
        return self._logger.filepath

    @property
    def source_id(self) -> str:
        return self._source_id

    def set_auto_reconnect(self, enabled: bool, interval: float = 5):
        """设置自动重连"""
        self._auto_reconnect = enabled
        self._reconnect_interval = interval

    def start(self):
        """启动连接"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """停止连接"""
        self._running = False
        self._close_connection()

        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

        self._logger.close()
        self._data_bus.unregister_log_handler(self._source_id)
        self._set_state(WorkerState.STOPPED)

    def write(self, data: str):
        """发送数据"""
        if self._tn and self._state == WorkerState.CONNECTED:
            try:
                self._tn.write(data.encode('utf-8'))
            except Exception as e:
                self.error_occurred.emit(f"发送失败: {e}")

    def send_command(self, command: str):
        """发送命令（自动添加换行）"""
        if not command.endswith('\n'):
            command += '\n'
        self.write(command)

    def _run(self):
        """工作线程主循环"""
        while self._running:
            try:
                self._connect()
                self._receive_loop()
            except Exception as e:
                self.error_occurred.emit(f"连接错误: {e}")
                self._set_state(WorkerState.ERROR)

            self._close_connection()

            if self._running and self._auto_reconnect:
                self._set_state(WorkerState.DISCONNECTED)
                time.sleep(self._reconnect_interval)
            else:
                break

    def _connect(self):
        """建立 Telnet 连接"""
        self._set_state(WorkerState.CONNECTING)

        # 根据 Python 版本选择实现
        if HAS_TELNETLIB:
            self._tn = telnetlib.Telnet(self.config.host, self.config.port, timeout=10)
        else:
            self._tn = SimpleTelnet(self.config.host, self.config.port, timeout=10)

        self._set_state(WorkerState.CONNECTED)

        # 自动登录（如果配置了用户名密码）
        if self.config.username:
            time.sleep(0.5)
            # 等待登录提示并发送用户名
            self._tn.read_until(b"login:", timeout=5)
            self._tn.write(f"{self.config.username}\n".encode())

            if self.config.password:
                self._tn.read_until(b"Password:", timeout=5)
                self._tn.write(f"{self.config.password}\n".encode())

    def _receive_loop(self):
        """接收数据循环"""
        while self._running and self._tn:
            try:
                data = self._tn.read_very_eager()
                if data:
                    text = data.decode('utf-8', errors='replace')
                    # 通过 DataBus 发布（异步，不阻塞）
                    self._data_bus.publish(self._source_id, text)
                    # 同时发信号（兼容旧代码）
                    self.data_received.emit(text)
                else:
                    time.sleep(0.001)

            except EOFError:
                # 连接关闭
                break
            except Exception as e:
                if self._running:
                    self.error_occurred.emit(f"接收错误: {e}")
                break

    def _close_connection(self):
        """关闭连接"""
        if self._tn:
            try:
                self._tn.close()
            except:
                pass
            self._tn = None

    def _set_state(self, state: WorkerState):
        """设置状态"""
        if self._state != state:
            self._state = state
            self.state_changed.emit(state)

    @staticmethod
    def is_available() -> bool:
        """检查 Telnet 功能是否可用"""
        return True  # 始终可用（有 SimpleTelnet 兜底）
