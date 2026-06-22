import json
from typing import List, Tuple


MSG_TYPE_DATA = 0x01
MSG_TYPE_PORT_LIST = 0x02
MSG_TYPE_PORT_ADD = 0x03
MSG_TYPE_PORT_REMOVE = 0x04
MSG_TYPE_SELECT_PORT = 0x05
MSG_TYPE_PORT_RENAME = 0x06
MSG_TYPE_LOG_LIST = 0x07
MSG_TYPE_LOG_LIST_RESPONSE = 0x08
MSG_TYPE_LOG_DOWNLOAD = 0x09
MSG_TYPE_LOG_DATA = 0x0A
MSG_TYPE_LOG_DOWNLOAD_DONE = 0x0B
MSG_TYPE_DEVICE_INFO = 0x0C
MSG_TYPE_BREAK = 0x0D
MSG_TYPE_AUTH = 0x0E
MSG_TYPE_AUTH_RESULT = 0x0F
MSG_TYPE_UNSELECT_PORT = 0x10


def encode_message(msg_type: int, port: str, data: str) -> bytes:
    payload = json.dumps({
        "type": msg_type,
        "port": port,
        "data": data,
    }).encode("utf-8")
    return len(payload).to_bytes(4, "big") + payload


def decode_message(data: bytes) -> dict:
    return json.loads(data.decode("utf-8"))


def extract_frames(buffer: bytes) -> Tuple[List[bytes], bytes]:
    frames = []
    offset = 0

    while len(buffer) - offset >= 4:
        msg_len = int.from_bytes(buffer[offset:offset + 4], "big")
        frame_start = offset + 4
        frame_end = frame_start + msg_len
        if len(buffer) < frame_end:
            break

        frames.append(buffer[frame_start:frame_end])
        offset = frame_end

    return frames, buffer[offset:]
