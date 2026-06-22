import json
import struct
from typing import Optional


ERR_OK = 0
ERR_PORT_NOT_FOUND = 1
ERR_PORT_NOT_OPEN = 2
ERR_TIMEOUT = 3
ERR_BAD_PARAMS = 4
ERR_INTERNAL = 5

MAX_MESSAGE_SIZE = 1024 * 1024


def encode_service_message(message: dict) -> bytes:
    payload = json.dumps(message, ensure_ascii=False).encode("utf-8")
    return struct.pack(">I", len(payload)) + payload


def decode_service_payload(payload: bytes) -> dict:
    return json.loads(payload.decode("utf-8"))


def read_exact(sock, size: int) -> Optional[bytes]:
    buffer = b""
    while len(buffer) < size:
        chunk = sock.recv(size - len(buffer))
        if not chunk:
            return None
        buffer += chunk
    return buffer


def recv_service_message(sock) -> Optional[dict]:
    header = read_exact(sock, 4)
    if not header:
        return None

    length = struct.unpack(">I", header)[0]
    if length > MAX_MESSAGE_SIZE:
        return None

    payload = read_exact(sock, length)
    if not payload:
        return None

    return decode_service_payload(payload)
