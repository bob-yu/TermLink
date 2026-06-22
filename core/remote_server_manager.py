from typing import Dict, Iterable, Optional


class RemoteServerManager:
    """Tracks GUI remote serial clients by normalized server id."""

    def __init__(self):
        self._clients: Dict[str, object] = {}
        self._active_server_id = ""

    @property
    def active_server_id(self) -> str:
        return self._active_server_id

    def set_active(self, server_id: str):
        if server_id in self._clients:
            self._active_server_id = server_id

    def add(self, server_id: str, client):
        self._clients[server_id] = client
        self._active_server_id = server_id

    def get(self, server_id: str):
        return self._clients.get(server_id)

    def connected_client(self, server_id: str):
        client = self.get(server_id)
        if client and getattr(client, "is_connected", False):
            return client
        return None

    def remove(self, server_id: str, disconnect: bool = True):
        client = self._clients.pop(server_id, None)
        if client and disconnect:
            client.disconnect()
        if self._active_server_id == server_id:
            self._active_server_id = next(iter(self._clients), "")
        return client

    def clear(self, disconnect: bool = True):
        for server_id in list(self._clients):
            self.remove(server_id, disconnect=disconnect)
        self._active_server_id = ""

    def clients(self) -> Dict[str, object]:
        return dict(self._clients)

    def server_ids(self) -> Iterable[str]:
        return list(self._clients.keys())

    def any_connected(self) -> bool:
        return any(getattr(client, "is_connected", False) for client in self._clients.values())

    def first_connected(self) -> Optional[tuple]:
        for server_id, client in self._clients.items():
            if getattr(client, "is_connected", False):
                return server_id, client
        return None
