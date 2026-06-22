import logging
from typing import Callable, Optional

from .serial_access_protocol import ERR_BAD_PARAMS, ERR_INTERNAL, ERR_OK
from .serial_access_service import SerialAccessService


logger = logging.getLogger(__name__)


_MAX_INFO_TEXT = 240


class SerialAccessApiRouter:
    """Dispatches action-style serial access API requests."""

    def __init__(
        self,
        access_service: Optional[SerialAccessService],
        subscribe: Callable[[str, str], None],
        unsubscribe: Callable[[str, str], None],
    ):
        self._access_service = access_service
        self._subscribe = subscribe
        self._unsubscribe = unsubscribe

    def dispatch(self, addr: str, action: str, params: dict) -> dict:
        port = params.get("port", "") if isinstance(params, dict) else ""
        source = params.get("source", "api") if isinstance(params, dict) else "api"
        logger.info(
            "Serial API request from %s: source=%s action=%s port=%s",
            addr,
            source,
            action,
            port or "-",
        )
        self._log_request_payload(source, action, params)
        result = self._dispatch(addr, action, params)
        logger.info(
            "Serial API response to %s: source=%s action=%s code=%s message=%s",
            addr,
            source,
            action,
            result.get("code"),
            result.get("message", ""),
        )
        self._log_response_payload(source, action, port, result)
        return result

    def _log_request_payload(self, source: str, action: str, params: dict):
        if not isinstance(params, dict):
            return
        if action in ("write", "write_data"):
            logger.info(
                "Serial API write request: source=%s port=%s data=%s",
                source,
                params.get("port", "-"),
                _preview_text(params.get("data", "")),
            )
        elif action in ("command", "send_command"):
            logger.info(
                "Serial API command request: source=%s port=%s command=%s",
                source,
                params.get("port", "-"),
                _preview_text(params.get("command", "")),
            )
        elif action == "watch":
            logger.info(
                "Serial API watch request: source=%s port=%s from=%s duration=%s expect=%s idle_timeout=%s start_seq=%s",
                source,
                params.get("port", "-"),
                params.get("from", "latest"),
                params.get("duration", 2.0),
                params.get("expect"),
                params.get("idle_timeout"),
                params.get("start_seq"),
            )

    def _log_response_payload(self, source: str, action: str, port: str, result: dict):
        data = result.get("data") if isinstance(result, dict) else None
        if action in ("list", "list_ports") and isinstance(data, list):
            ports = ", ".join(item.get("port", "") for item in data if isinstance(item, dict))
            logger.info("Serial API list response: source=%s ports=%s", source, ports or "-")
            return
        if action in ("state", "get_port_state") and isinstance(data, dict):
            logger.info(
                "Serial API state response: source=%s port=%s physical=%s run=%s ip=%s",
                source,
                port or "-",
                data.get("physical_state", "-"),
                data.get("device_run_state", "-"),
                data.get("device_ip", ""),
            )
            return
        if action in ("buffer_state", "buffer-state", "buffer") and isinstance(data, dict):
            logger.info(
                "Serial API buffer response: source=%s port=%s bytes=%s/%s oldest_seq=%s latest_seq=%s dropped_chunks=%s dropped_bytes=%s",
                source,
                port or "-",
                data.get("current_bytes", 0),
                data.get("max_bytes", 0),
                data.get("oldest_seq", 0),
                data.get("latest_seq", 0),
                data.get("dropped_chunks", 0),
                data.get("dropped_bytes", 0),
            )
            return
        if action in ("watch", "command", "send_command") and isinstance(data, dict):
            output = data.get("output", "")
            logger.info(
                "Serial API output response: source=%s action=%s port=%s bytes=%d reason=%s matched=%s preview=%s",
                source,
                action,
                port or "-",
                len(output.encode("utf-8", errors="replace")),
                data.get("reason", "-"),
                data.get("matched", False),
                _preview_text(output),
            )
            if output:
                logger.debug(
                    "Serial API output full: source=%s action=%s port=%s\n%s",
                    source,
                    action,
                    port or "-",
                    output,
                )
            return
        if action in ("log", "get_log_snapshot") and isinstance(data, dict):
            content = data.get("content", "")
            logger.info(
                "Serial API log response: source=%s port=%s bytes=%d preview=%s",
                source,
                port or "-",
                len(content.encode("utf-8", errors="replace")),
                _preview_text(content),
            )
            if content:
                logger.debug("Serial API log full: source=%s port=%s\n%s", source, port or "-", content)

    def _dispatch(self, addr: str, action: str, params: dict) -> dict:
        if not self._access_service:
            return {"code": ERR_INTERNAL, "message": "Serial access service is unavailable"}

        if action in ("list_ports", "list"):
            return self._access_service.list_ports()
        if action in ("get_port_state", "state"):
            return self._access_service.get_port_state(params.get("port", ""))
        if action in ("find_port_by_ip", "find_ip"):
            return self._access_service.find_ports(params.get("device_ip", ""))
        if action in ("write_data", "write"):
            return self._access_service.write(params.get("port", ""), params.get("data", ""))
        if action == "watch":
            return self._access_service.watch(
                params.get("port", ""),
                duration=params.get("duration", 2.0),
                expect=params.get("expect", None),
                idle_timeout=params.get("idle_timeout", None),
                start_seq=params.get("start_seq", None),
                from_position=params.get("from", "latest"),
                regex=params.get("regex", False),
            )
        if action in ("buffer_state", "buffer-state", "buffer"):
            return self._access_service.buffer_state(params.get("port", ""))
        if action in ("send_command", "command"):
            return self._access_service.send_command(
                params.get("port", ""),
                params.get("command", ""),
                params.get("expect", None),
                params.get("timeout", 30),
                duration=params.get("duration", None),
                idle_timeout=params.get("idle_timeout", None),
                regex=params.get("regex", False),
            )
        if action in ("send_break", "break"):
            return self._access_service.send_break(params.get("port", ""))
        if action in ("get_log_snapshot", "log"):
            return self._access_service.get_log_snapshot(params.get("port", ""), params.get("lines", 100))
        if action == "update_device_ip":
            return self._access_service.update_device_info(
                params.get("port", ""),
                device_ip=params.get("device_ip", ""),
            )
        if action == "fetch_device_ip":
            return self._access_service.fetch_device_info(
                params.get("port", ""),
                timeout=params.get("timeout", 10),
            )
        if action == "subscribe":
            port = params.get("port", "")
            if not port:
                return {"code": ERR_BAD_PARAMS, "message": "Missing port parameter"}
            self._subscribe(addr, port)
            return {"code": ERR_OK, "message": "ok"}
        if action == "unsubscribe":
            port = params.get("port", "")
            if not port:
                return {"code": ERR_BAD_PARAMS, "message": "Missing port parameter"}
            self._unsubscribe(addr, port)
            return {"code": ERR_OK, "message": "ok"}

        return {"code": ERR_BAD_PARAMS, "message": f"Unknown action: {action}"}


def _preview_text(value) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\r", "\\r").replace("\n", "\\n")
    if len(text) <= _MAX_INFO_TEXT:
        return text
    return text[:_MAX_INFO_TEXT] + f"... <truncated {len(text) - _MAX_INFO_TEXT} chars>"
