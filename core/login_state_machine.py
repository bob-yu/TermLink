"""Login state machine for serial devices."""
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, List, Optional


class LoginState(Enum):
    """Login state."""

    IDLE = auto()
    WAIT_LOGIN = auto()
    WAIT_PASSWORD = auto()
    WAIT_SHELL = auto()
    READY = auto()
    FAILED = auto()


@dataclass
class LoginConfig:
    """Login prompt and credential configuration."""

    username: str = "root"
    password: str = "root"
    login_prompt: str = "login:"
    password_prompt: str = "Password:"
    shell_prompts: List[str] = None
    timeout: float = 30.0

    def __post_init__(self):
        if self.shell_prompts is None:
            self.shell_prompts = ["#", "$"]


class LoginStateMachine:
    """Small automatic login state machine.

    Normal transition:
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
            self._state = new_state
            if self._on_state_change_callback:
                self._on_state_change_callback(new_state)

    def set_send_callback(self, callback: Callable[[str], None]):
        """Set the callback used to send login data."""
        self._on_send_callback = callback

    def set_state_change_callback(self, callback: Callable[[LoginState], None]):
        """Set the state-change callback."""
        self._on_state_change_callback = callback

    def start(self):
        """Start the login flow."""
        self._buffer = ""
        self._retry_count = 0
        self.state = LoginState.WAIT_LOGIN

    def reset(self):
        """Reset the state machine."""
        self._buffer = ""
        self._retry_count = 0
        self.state = LoginState.IDLE

    def feed(self, data: str) -> Optional[str]:
        """Feed serial data and return data that should be sent back."""
        if self._state == LoginState.IDLE or self._state == LoginState.READY:
            return None

        self._buffer += data

        if len(self._buffer) > 8192:
            self._buffer = self._buffer[-4096:]

        response = None

        if self._state == LoginState.WAIT_LOGIN:
            response = self._handle_wait_login()
        elif self._state == LoginState.WAIT_PASSWORD:
            response = self._handle_wait_password()
        elif self._state == LoginState.WAIT_SHELL:
            response = self._handle_wait_shell()

        if response and self._on_send_callback:
            self._on_send_callback(response)

        return response

    def _handle_wait_login(self) -> Optional[str]:
        """Handle the login prompt state."""
        if self._has_login_prompt():
            self._buffer = ""
            self.state = LoginState.WAIT_PASSWORD
            return self.config.username + "\n"
        if self._has_shell_prompt():
            self._mark_ready()
            return None
        return None

    def _handle_wait_password(self) -> Optional[str]:
        """Handle the password prompt state."""
        if self._has_password_prompt():
            self._buffer = ""
            self.state = LoginState.WAIT_SHELL
            return self.config.password + "\n"
        elif self._has_login_prompt():
            self._retry_count += 1
            if self._retry_count >= self._max_retries:
                self.state = LoginState.FAILED
                return None
            self._buffer = ""
            return self.config.username + "\n"
        if self._has_shell_prompt():
            self._mark_ready()
            return None
        return None

    def _handle_wait_shell(self) -> Optional[str]:
        """Handle the shell prompt state."""
        if self._has_shell_prompt():
            self._mark_ready()
            return None
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
        """Return whether login succeeded."""
        return self._state == LoginState.READY

    def is_failed(self) -> bool:
        """Return whether login failed."""
        return self._state == LoginState.FAILED
