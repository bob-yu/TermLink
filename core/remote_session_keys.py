REMOTE_SESSION_PREFIX = "remote://"


def is_remote_session_key(key: str) -> bool:
    return key.startswith(REMOTE_SESSION_PREFIX)


def make_remote_session_key(port: str, server_id: str = "") -> str:
    if server_id:
        return f"{REMOTE_SESSION_PREFIX}{server_id}/{port}"
    return f"{REMOTE_SESSION_PREFIX}{port}"


def parse_remote_session_key(key: str):
    if not is_remote_session_key(key):
        return "", key
    value = key[len(REMOTE_SESSION_PREFIX):]
    if "/" not in value:
        return "", value
    server_id, port = value.rsplit("/", 1)
    return server_id, port


def remote_session_server_id(key: str) -> str:
    server_id, _port = parse_remote_session_key(key)
    return server_id


def remote_session_port(key: str) -> str:
    _server_id, port = parse_remote_session_key(key)
    return port


def remote_tab_name(port: str) -> str:
    port_name = port.split("/")[-1] if "/" in port else port
    return f"Remote:{port_name}"
