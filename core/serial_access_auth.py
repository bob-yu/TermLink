import json
from typing import Callable, Dict


class SerialAccessAuthState:
    """Tracks per-client authentication for the serial access server."""

    def __init__(self, password_provider: Callable[[], str]):
        self._password_provider = password_provider
        self.authorized: Dict[str, bool] = {}

    def add_client(self, addr: str) -> bool:
        is_authorized = not bool(self._password_provider())
        self.authorized[addr] = is_authorized
        return is_authorized

    def remove_client(self, addr: str):
        self.authorized.pop(addr, None)

    def clear(self):
        self.authorized.clear()

    def is_authorized(self, addr: str) -> bool:
        return self.authorized.get(addr, False)

    def set_authorized(self, addr: str, authorized: bool):
        self.authorized[addr] = authorized

    def authenticate_payload(self, addr: str, data: str) -> bool:
        try:
            payload = json.loads(data) if data else {}
        except Exception:
            payload = {}

        password = self._password_provider()
        authorized = (not password) or payload.get("password", "") == password
        self.set_authorized(addr, authorized)
        return authorized

    def authenticate_params(self, addr: str, params: dict) -> bool:
        password = self._password_provider()
        authorized = (not password) or params.get("password", "") == password
        self.set_authorized(addr, authorized)
        return authorized
