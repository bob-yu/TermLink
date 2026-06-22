import json
from typing import Callable

from .network_log_files import get_log_files, read_log_file_chunk
from .network_protocol import MSG_TYPE_LOG_DATA, MSG_TYPE_LOG_LIST_RESPONSE


class SerialAccessLogRouter:
    """Handles remote log listing and chunk download requests."""

    def __init__(
        self,
        log_dir_provider: Callable[[], str],
        send_gui_message: Callable[[str, int, str, str], None],
        emit_error: Callable[[str], None],
    ):
        self._log_dir_provider = log_dir_provider
        self._send_gui_message = send_gui_message
        self._emit_error = emit_error

    def handle_list_request(self, addr: str):
        try:
            log_dir = self._log_dir_provider()
            files = get_log_files(log_dir)
            print(f"[SerialAccessServer] Log list request from {addr}, found {len(files)} files in {log_dir}")
            self._send_gui_message(addr, MSG_TYPE_LOG_LIST_RESPONSE, "", json.dumps(files))
        except Exception as exc:
            print(f"[SerialAccessServer] Get log list failed: {exc}")
            self._emit_error(f"获取日志列表失败: {exc}")

    def handle_download_request(self, addr: str, request_data: str):
        try:
            req = json.loads(request_data)
            filename = req.get("filename", "")
            offset = req.get("offset", 0)
            chunk_size = req.get("chunk_size", 65536)
            chunk = read_log_file_chunk(self._log_dir_provider(), filename, offset, chunk_size)

            response = json.dumps({
                "filename": filename,
                "offset": offset,
                "size": len(chunk),
                "data": chunk.hex(),
            })
            self._send_gui_message(addr, MSG_TYPE_LOG_DATA, "", response)
        except Exception as exc:
            self._emit_error(f"下载日志失败: {exc}")
