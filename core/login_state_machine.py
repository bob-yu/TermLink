"""
登录状态机模块
实现串口设备的自动登录逻辑
"""
from enum import Enum, auto
from typing import Optional, List, Callable
from dataclasses import dataclass


class LoginState(Enum):
    """登录状态枚举"""
    IDLE = auto()           # 空闲状态
    WAIT_LOGIN = auto()     # 等待login提示
    WAIT_PASSWORD = auto()  # 等待password提示
    WAIT_SHELL = auto()     # 等待shell提示符
    READY = auto()          # 登录成功，就绪
    FAILED = auto()         # 登录失败


@dataclass
class LoginConfig:
    """登录配置"""
    username: str = "root"
    password: str = "root"
    login_prompt: str = "login:"
    password_prompt: str = "Password:"
    shell_prompts: List[str] = None
    timeout: float = 30.0  # 登录超时时间（秒）

    def __post_init__(self):
        if self.shell_prompts is None:
            self.shell_prompts = ["#", "$"]


class LoginStateMachine:
    """
    登录状态机

    状态转换流程:
    IDLE -> WAIT_LOGIN -> WAIT_PASSWORD -> WAIT_SHELL -> READY
                                                      -> FAILED
    """

    def __init__(self, config: LoginConfig = None):
        self.config = config or LoginConfig()
        self._state = LoginState.IDLE
        self._buffer = ""
        self._on_send_callback: Optional[Callable[[str], None]] = None
        self._on_state_change_callback: Optional[Callable[[LoginState], None]] = None
        self._retry_count = 0
        self._max_retries = 3

    @property
    def state(self) -> LoginState:
        return self._state

    @state.setter
    def state(self, new_state: LoginState):
        if self._state != new_state:
            old_state = self._state
            self._state = new_state
            if self._on_state_change_callback:
                self._on_state_change_callback(new_state)

    def set_send_callback(self, callback: Callable[[str], None]):
        """设置发送数据的回调函数"""
        self._on_send_callback = callback

    def set_state_change_callback(self, callback: Callable[[LoginState], None]):
        """设置状态变化的回调函数"""
        self._on_state_change_callback = callback

    def start(self):
        """开始登录流程"""
        self._buffer = ""
        self._retry_count = 0
        self.state = LoginState.WAIT_LOGIN

    def reset(self):
        """重置状态机"""
        self._buffer = ""
        self._retry_count = 0
        self.state = LoginState.IDLE

    def feed(self, data: str) -> Optional[str]:
        """
        输入数据到状态机

        Args:
            data: 从串口接收到的数据

        Returns:
            需要发送的响应数据，如果不需要发送则返回None
        """
        if self._state == LoginState.IDLE or self._state == LoginState.READY:
            return None

        self._buffer += data

        # 限制缓冲区大小，防止内存泄漏
        if len(self._buffer) > 8192:
            self._buffer = self._buffer[-4096:]

        response = None

        if self._state == LoginState.WAIT_LOGIN:
            response = self._handle_wait_login()
        elif self._state == LoginState.WAIT_PASSWORD:
            response = self._handle_wait_password()
        elif self._state == LoginState.WAIT_SHELL:
            response = self._handle_wait_shell()

        # 如果有响应需要发送
        if response and self._on_send_callback:
            self._on_send_callback(response)

        return response

    def _handle_wait_login(self) -> Optional[str]:
        """处理等待login提示状态"""
        if self._has_login_prompt():
            self._buffer = ""
            self.state = LoginState.WAIT_PASSWORD
            return self.config.username + "\n"
        # BUG FIX: 如果已经在 shell 中（直接看到 # 或 $），跳过登录
        if self._has_shell_prompt():
            self._mark_ready()
            return None
        return None

    def _handle_wait_password(self) -> Optional[str]:
        """处理等待password提示状态"""
        if self._has_password_prompt():
            self._buffer = ""
            self.state = LoginState.WAIT_SHELL
            return self.config.password + "\n"
        # 如果又出现login提示，说明用户名错误
        elif self._has_login_prompt():
            self._retry_count += 1
            if self._retry_count >= self._max_retries:
                self.state = LoginState.FAILED
                return None
            self._buffer = ""
            # BUG FIX: 状态应该保持在 WAIT_PASSWORD，而不是再设置一次
            # 并且应该重新发送用户名
            return self.config.username + "\n"
        # BUG FIX: 如果直接看到 shell 提示符（无密码登录），跳过
        if self._has_shell_prompt():
            self._mark_ready()
            return None
        return None

    def _handle_wait_shell(self) -> Optional[str]:
        """处理等待shell提示符状态"""
        if self._has_shell_prompt():
            self._mark_ready()
            return None
        # 如果又出现login提示，说明密码错误
        if self._has_login_prompt():
            self._retry_count += 1
            if self._retry_count >= self._max_retries:
                self.state = LoginState.FAILED
                return None
            self._buffer = ""
            self.state = LoginState.WAIT_PASSWORD
            return self.config.username + "\n"
        return None

    def _has_login_prompt(self) -> bool:
        return self.config.login_prompt.lower() in self._buffer.lower()

    def _has_password_prompt(self) -> bool:
        return self.config.password_prompt.lower() in self._buffer.lower()

    def _has_shell_prompt(self) -> bool:
        return any(prompt in self._buffer for prompt in self.config.shell_prompts)

    def _mark_ready(self):
        self._buffer = ""
        self.state = LoginState.READY

    def is_ready(self) -> bool:
        """是否登录成功"""
        return self._state == LoginState.READY

    def is_failed(self) -> bool:
        """是否登录失败"""
        return self._state == LoginState.FAILED
