import logging
import time
from typing import Callable, Optional

from .log_snapshot import read_last_lines
from .remote_session_keys import is_remote_session_key
from .serial_output_buffer import SerialOutputBuffer
from .serial_access_protocol import (
    ERR_BAD_PARAMS,
    ERR_INTERNAL,
    ERR_OK,
    ERR_PORT_NOT_FOUND,
    ERR_PORT_NOT_OPEN,
    ERR_TIMEOUT,
)

logger = logging.getLogger(__name__)


class SerialAccessService:
    """Application service for local serial access operations.

    This class owns the business API. Socket servers, GUI actions, and future
    transports should delegate here instead of touching MainWindow sessions
    directly.
    """

    def __init__(
        self,
        sessions_provider: Callable[[], dict],
        output_buffer: Optional[SerialOutputBuffer] = None,
    ):
        self._sessions_provider = sessions_provider
        self._output_buffer = output_buffer

    def list_ports(self) -> dict:
        sessions = self._get_sessions()
        if sessions is None:
            return {"code": ERR_INTERNAL, "message": "Unable to read serial sessions"}

        ports = []
        for port_path, (worker, _tab, config) in sessions.items():
            if self._is_remote_or_network_session(port_path):
                continue
            state = worker.get_full_device_state()
            ports.append({
                "port": port_path,
                "name": config.name if config else port_path,
                "physical_state": state.get("physical_state", "UNKNOWN"),
                "device_run_state": state.get("device_run_state", "UNKNOWN"),
                "device_ip": state.get("device_ip", ""),
                "device_version": state.get("device_version", ""),
            })
        return {"code": ERR_OK, "message": "ok", "data": ports}

    def get_port_state(self, port: str) -> dict:
        if not port:
            return {"code": ERR_BAD_PARAMS, "message": "Missing port parameter"}
        worker = self._get_worker(port)
        if not worker:
            return {"code": ERR_PORT_NOT_FOUND, "message": f"Port not found: {port}"}
        return {"code": ERR_OK, "message": "ok", "data": worker.get_full_device_state()}

    def find_ports(self, device_ip: str = "") -> dict:
        if not device_ip:
            return {"code": ERR_BAD_PARAMS, "message": "Missing device_ip parameter"}
        sessions = self._get_sessions()
        if sessions is None:
            return {"code": ERR_INTERNAL, "message": "Unable to read serial sessions"}

        matches = []
        for port_path, (worker, _tab, config) in sessions.items():
            if self._is_remote_or_network_session(port_path):
                continue
            state = worker.get_full_device_state()
            if state.get("device_ip") == device_ip:
                matches.append({
                    "port": port_path,
                    "name": config.name if config else port_path,
                    "state": state,
                })

        if not matches:
            return {"code": ERR_PORT_NOT_FOUND, "message": f"No port found for IP={device_ip}"}
        return {"code": ERR_OK, "message": "ok", "data": matches[0] if len(matches) == 1 else matches}

    def write(self, port: str, data: str) -> dict:
        worker_result = self._require_open_worker(port)
        if isinstance(worker_result, dict):
            return worker_result
        worker_result.write(data)
        return {"code": ERR_OK, "message": "ok"}

    def watch(
        self,
        port: str,
        duration: float = 2.0,
        expect=None,
        idle_timeout=None,
        start_seq=None,
        from_position: str = "latest",
        regex: bool = False,
    ) -> dict:
        if not port:
            return {"code": ERR_BAD_PARAMS, "message": "Missing port parameter"}
        if from_position not in ("latest", "oldest", "seq"):
            return {"code": ERR_BAD_PARAMS, "message": "from must be one of: latest, oldest, seq"}
        if from_position == "seq" and start_seq is None:
            return {"code": ERR_BAD_PARAMS, "message": "start_seq is required when from=seq"}
        worker = self._get_worker(port)
        if not worker:
            return {"code": ERR_PORT_NOT_FOUND, "message": f"Port not found: {port}"}
        if not self._output_buffer:
            return {"code": ERR_INTERNAL, "message": "Serial output buffer is unavailable"}

        data = self._output_buffer.watch(
            port=port,
            start_seq=start_seq,
            from_position=from_position,
            duration=duration,
            expect=expect,
            idle_timeout=idle_timeout,
            regex=regex,
        )
        return {"code": ERR_OK, "message": "ok", "data": data}

    def buffer_state(self, port: str) -> dict:
        if not port:
            return {"code": ERR_BAD_PARAMS, "message": "Missing port parameter"}
        worker = self._get_worker(port)
        if not worker:
            return {"code": ERR_PORT_NOT_FOUND, "message": f"Port not found: {port}"}
        if not self._output_buffer:
            return {"code": ERR_INTERNAL, "message": "Serial output buffer is unavailable"}
        return {"code": ERR_OK, "message": "ok", "data": self._output_buffer.state(port)}

    def send_command(
        self,
        port: str,
        command: str,
        expect=None,
        timeout: int = 30,
        duration=None,
        idle_timeout=None,
        regex: bool = False,
    ) -> dict:
        worker_result = self._require_open_worker(port)
        if isinstance(worker_result, dict):
            return worker_result
        worker = worker_result
        start_seq = self._output_buffer.latest_seq(port) if self._output_buffer else None
        worker.send_command(command)

        if not self._output_buffer:
            return {"code": ERR_OK, "message": "ok", "data": {"output": "", "matched": not bool(expect)}}

        watch_result = self._output_buffer.watch(
            port=port,
            start_seq=start_seq,
            duration=duration if duration is not None else timeout,
            expect=expect,
            idle_timeout=idle_timeout,
            regex=regex,
        )
        code = ERR_OK
        message = "ok"
        if expect and not watch_result.get("matched"):
            code = ERR_TIMEOUT
            message = f"Timeout waiting for '{expect}'"
        return {"code": code, "message": message, "data": watch_result}

    def send_break(self, port: str) -> dict:
        worker_result = self._require_open_worker(port)
        if isinstance(worker_result, dict):
            return worker_result
        worker_result.send_break()
        return {"code": ERR_OK, "message": "ok"}

    def get_log_snapshot(self, port: str, lines: int = 100) -> dict:
        if not port:
            return {"code": ERR_BAD_PARAMS, "message": "Missing port parameter"}
        worker = self._get_worker(port)
        if not worker:
            return {"code": ERR_PORT_NOT_FOUND, "message": f"Port not found: {port}"}
        content = read_last_lines(worker.log_filepath, lines)
        return {"code": ERR_OK, "message": "ok", "data": {"content": content}}

    def update_device_info(self, port: str, device_ip: str = "") -> dict:
        if not port:
            return {"code": ERR_BAD_PARAMS, "message": "Missing port parameter"}
        if not device_ip:
            return {"code": ERR_BAD_PARAMS, "message": "Missing device_ip parameter"}
        worker = self._get_worker(port)
        if not worker:
            return {"code": ERR_PORT_NOT_FOUND, "message": f"Port not found: {port}"}
        if not hasattr(worker, "_device_state"):
            return {"code": ERR_INTERNAL, "message": "Device state is unavailable"}

        old_ip = worker._device_state.device_ip
        worker._device_state.device_ip = device_ip
        logger.info("Updated device IP [%s]: %s -> %s", port, old_ip, device_ip)
        return {"code": ERR_OK, "message": "ok", "data": {"old_ip": old_ip, "new_ip": device_ip}}

    def fetch_device_info(self, port: str, timeout: int = 10) -> dict:
        if not port:
            return {"code": ERR_BAD_PARAMS, "message": "Missing port parameter"}
        worker = self._get_worker(port)
        if not worker:
            return {"code": ERR_PORT_NOT_FOUND, "message": f"Port not found: {port}"}

        try:
            worker.write("\n")
            time.sleep(0.3)
            worker.write("ifconfig\n")
            time.sleep(min(max(timeout, 1), 2))

            if hasattr(worker, "_device_state") and worker._device_state.device_ip:
                return {
                    "code": ERR_OK,
                    "message": "ok",
                    "data": {"ip": worker._device_state.device_ip},
                }
            return {"code": ERR_OK, "message": "fetching"}
        except Exception as exc:
            logger.error("Fetch device info failed [%s]: %s", port, exc)
            return {"code": ERR_TIMEOUT, "message": f"Fetch failed: {exc}"}

    def check_hung_ports(self):
        sessions = self._get_sessions()
        if not sessions:
            return
        for port_path, (worker, _tab, _config) in sessions.items():
            if self._is_remote_or_network_session(port_path):
                continue
            if hasattr(worker, "_device_state"):
                worker._device_state.check_hung()

    def _require_open_worker(self, port: str):
        if not port:
            return {"code": ERR_BAD_PARAMS, "message": "Missing port parameter"}
        worker = self._get_worker(port)
        if not worker:
            return {"code": ERR_PORT_NOT_FOUND, "message": f"Port not found: {port}"}
        if not worker.is_connected:
            return {"code": ERR_PORT_NOT_OPEN, "message": f"Port is not open: {port}"}
        return worker

    def _get_sessions(self) -> Optional[dict]:
        if not self._sessions_provider:
            return None
        try:
            return self._sessions_provider()
        except Exception as exc:
            logger.error("Read serial sessions failed: %s", exc)
            return None

    def _get_worker(self, port: str):
        sessions = self._get_sessions()
        if not sessions:
            return None
        entry = sessions.get(port)
        if entry:
            return entry[0]
        return None

    @staticmethod
    def _is_remote_or_network_session(port_path: str) -> bool:
        return is_remote_session_key(port_path) or port_path.startswith(("ssh://", "telnet://"))
