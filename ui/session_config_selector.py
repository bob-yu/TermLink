from core.remote_session_keys import is_remote_session_key


def serial_port_configs_to_save(sessions: dict):
    """Return local serial port configs that should be persisted."""
    return [
        config
        for key, (_worker, _tab, config) in sessions.items()
        if config is not None and not is_remote_session_key(key) and not _is_network_terminal_key(key)
    ]


def _is_network_terminal_key(key: str) -> bool:
    return key.startswith(("ssh://", "telnet://", "rawtcp://"))
