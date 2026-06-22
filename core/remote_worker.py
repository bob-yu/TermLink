"""
远程串口工作模块
通过网络连接远程串口，提供与本地串口相同的接口
"""
import socket
import threading
import json
import time
from typing import Optional, List, Dict
from dataclasses import dataclass

from PyQt5.QtCore import QObject, pyqtSignal

from .serial_worker import WorkerState
from .login_state_machine import LoginStateMachine, LoginConfig, LoginState
from .network_protocol import MSG_TYPE_DATA, MSG_TYPE_SELECT_PORT, decode_message, encode_message
from .serial_access_client import SerialAccessClient


@dataclass
class RemoteSerialConfig:
    """远程串口配置"""
    server_host: str
    server_port: int
    remote_port: str = ""  # 远程串口名称
    name: str = "Remote"


class RemoteSerialWorkerProxy(QObject):
    """
    远程串口代理
    共用一个 SerialAccessClient，每个远程串口一个代理实例
    提供与 SerialWorker 相同的接口
    """

    # Qt信号定义（与 SerialWorker 相同）
    data_received = pyqtSignal(str)           # 接收到数据
    state_changed = pyqtSignal(WorkerState)   # 状态变化
    login_state_changed = pyqtSignal(LoginState)  # 登录状态变化
    error_occurred = pyqtSignal(str)          # 错误信息
    keyword_detected = pyqtSignal(str, str)   # (关键字类型, 匹配行)

    def __init__(self, network_client: SerialAccessClient, remote_port: str):
        super().__init__()
        self._network_client = network_client
        self._remote_port = remote_port
        self._state = WorkerState.CONNECTED if network_client.is_connected else WorkerState.STOPPED

        # 登录状态机
        self._login_machine: Optional[LoginStateMachine] = None
        self._auto_login_enabled = False

        # 自动执行命令列表
        self._auto_commands: List[str] = []

        # 关键字检测
        self._keywords: Dict[str, List[str]] = {}

        # 配置对象（兼容 SerialWorker）
        self.config = type('Config', (), {
            'port': remote_port,
            'baudrate': 115200,
            'name': remote_port
        })()

    @property
    def state(self) -> WorkerState:
        return self._state

    @property
    def is_connected(self) -> bool:
        return (
            self._state == WorkerState.CONNECTED
            and self._network_client
            and self._network_client.is_connected
        )

    @property
    def log_filepath(self) -> str:
        return ""

    def setup_login(self, login_config: LoginConfig):
        """设置登录配置"""
        self._login_machine = LoginStateMachine(login_config)
        self._login_machine.set_send_callback(self.write)
        self._login_machine.set_state_change_callback(self._on_login_state_change)
        self._auto_login_enabled = True

    def set_auto_commands(self, commands: List[str]):
        """设置自动执行命令列表"""
        self._auto_commands = commands.copy()

    def set_keywords(self, keywords: Dict[str, List[str]]):
        """设置关键字检测"""
        self._keywords = keywords.copy()

    def set_auto_reconnect(self, enabled: bool, interval: float = 5):
        """设置自动重连（代理模式下由 SerialAccessClient 处理）"""
        pass

    def start(self):
        """启动（代理模式下不需要）"""
        if self._network_client and self._network_client.is_connected:
            self._network_client.select_port(self._remote_port)
            self._state = WorkerState.CONNECTED
            self.state_changed.emit(self._state)
            return
        self._state = WorkerState.DISCONNECTED
        self.state_changed.emit(self._state)

    def stop(self):
        """停止"""
        if self._network_client and self._network_client.is_connected:
            self._network_client.unselect_port(self._remote_port)
        self._state = WorkerState.STOPPED
        self.state_changed.emit(self._state)

    def write(self, data: str):
        """发送数据到远程串口"""
        if not self._network_client or not self._network_client.is_connected:
            return

        # 通过网络客户端发送，指定目标串口
        self._network_client.send_to_port(self._remote_port, data)

    def send_command(self, command: str):
        """发送命令（自动添加换行符）"""
        if not command.endswith('\n'):
            command += '\n'
        self.write(command)

    def send_break(self):
        """发送 Break 信号到远程串口"""
        if not self._network_client or not self._network_client.is_connected:
            return
        self._network_client.send_break(self._remote_port)

    def start_login(self):
        """开始登录流程"""
        if self._login_machine:
            self._login_machine.start()

    def feed_data(self, data: str):
        """外部喂入数据（由主窗口调用）"""
        # 发送信号
        self.data_received.emit(data)

        # 检测关键字
        self._check_keywords(data)

        # 处理登录状态机
        if self._auto_login_enabled and self._login_machine:
            self._login_machine.feed(data)

    def _on_login_state_change(self, state: LoginState):
        """登录状态变化回调"""
        self.login_state_changed.emit(state)

        # 登录成功后执行自动命令
        if state == LoginState.READY:
            self._execute_auto_commands()

    def _execute_auto_commands(self):
        """执行自动命令列表"""
        if not self._auto_commands:
            return

        for cmd in self._auto_commands:
            self.send_command(cmd)

    def _check_keywords(self, text: str):
        """检测关键字"""
        for keyword_type, keywords in self._keywords.items():
            for keyword in keywords:
                if keyword in text:
                    for line in text.split('\n'):
                        if keyword in line:
                            self.keyword_detected.emit(keyword_type, line.strip())

    @staticmethod
    def list_ports() -> List[str]:
        """列出可用串口（远程模式返回空）"""
        return []
