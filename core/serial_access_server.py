"""
串口访问服务模块
实现串口数据的网络转发（服务端/客户端）
支持多串口，每个串口独立通道
"""
import socket
import threading
import json
import time
from typing import Optional, Callable, List, Dict
from dataclasses import dataclass
from enum import Enum, auto

from PyQt5.QtCore import QObject, pyqtSignal

from utils.config_schema import DEFAULT_REMOTE_SERIAL_PORT

from .network_protocol import (
    MSG_TYPE_AUTH,
    MSG_TYPE_AUTH_RESULT,
    MSG_TYPE_BREAK,
    MSG_TYPE_DATA,
    MSG_TYPE_DEVICE_INFO,
    MSG_TYPE_LOG_DOWNLOAD,
    MSG_TYPE_LOG_LIST,
    MSG_TYPE_PORT_ADD,
    MSG_TYPE_PORT_LIST,
    MSG_TYPE_PORT_REMOVE,
    MSG_TYPE_PORT_RENAME,
    MSG_TYPE_SELECT_PORT,
    MSG_TYPE_UNSELECT_PORT,
    decode_message,
    encode_message,
    extract_frames,
)
from .serial_access_client import SerialAccessClient
from .serial_access_api_router import SerialAccessApiRouter
from .serial_access_auth import SerialAccessAuthState
from .serial_access_log_router import SerialAccessLogRouter
from .serial_access_permissions import (
    PERMISSION_READ_ONLY,
    PERMISSION_READ_WRITE,
    WRITE_ACTIONS,
    SerialAccessClientInfo,
    client_ip,
    normalize_permission,
)
from .serial_access_service import SerialAccessService
from .serial_output_buffer import SerialOutputBuffer
from .serial_access_protocol import (
    ERR_BAD_PARAMS,
    ERR_INTERNAL,
    encode_service_message,
)


class SerialAccessMode(Enum):
    """网络模式"""
    DISABLED = auto()   # 禁用网络
    SERVER = auto()     # 服务端模式
    CLIENT = auto()     # 客户端模式


@dataclass
class SerialAccessConfig:
    """网络配置"""
    mode: SerialAccessMode = SerialAccessMode.DISABLED
    host: str = "0.0.0.0"  # 服务端监听地址
    port: int = DEFAULT_REMOTE_SERIAL_PORT       # 端口
    server_host: str = ""  # 客户端连接的服务器地址


class SerialAccessServer(QObject):
    """
    网络服务端
    将本地串口数据转发给远程客户端
    支持多串口，带数据缓冲降低网络传输频率
    """
    client_connected = pyqtSignal(str)      # 客户端连接
    client_disconnected = pyqtSignal(str)   # 客户端断开
    client_updated = pyqtSignal(str)        # 客户端状态更新
    data_received = pyqtSignal(str, str, str)  # 收到客户端数据 (client_addr, port, data)
    error_occurred = pyqtSignal(str)        # 错误

    # 客户端刷新配置（比本地慢，节省带宽）
    CLIENT_REFRESH_INTERVAL = 0.05  # 50ms，约 20fps
    BUFFER_FLUSH_SIZE = 2048        # 2KB 强制刷新

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = DEFAULT_REMOTE_SERIAL_PORT,
        log_dir: str = "logs",
        sessions_provider: Optional[Callable] = None,
        access_password: str = "",
        max_clients: int = 16,
        default_permission: str = PERMISSION_READ_WRITE,
        banned_ips: Optional[List[str]] = None,
    ):
        super().__init__()
        self.host = host
        self.port = port
        self.log_dir = log_dir  # 服务端日志目录
        self.access_password = access_password
        self.max_clients = max(1, int(max_clients))
        self.default_permission = normalize_permission(default_permission)
        self._banned_ips = set(banned_ips or [])
        self._output_buffer = SerialOutputBuffer()
        self._access_service = (
            SerialAccessService(sessions_provider, self._output_buffer)
            if sessions_provider
            else None
        )
        self._server_socket: Optional[socket.socket] = None
        self._clients: Dict[str, socket.socket] = {}  # addr -> socket
        self._auth = SerialAccessAuthState(lambda: self.access_password)
        self._client_authorized = self._auth.authorized
        self._client_selected_port: Dict[str, str] = {}  # addr -> selected_port
        self._client_open_ports: Dict[str, set] = {}  # addr -> opened remote ports
        self._client_permissions: Dict[str, str] = {}  # addr -> permission
        self._client_connected_at: Dict[str, float] = {}
        self._client_last_active: Dict[str, float] = {}
        self._client_read_counts: Dict[str, int] = {}
        self._client_write_counts: Dict[str, int] = {}
        self._api_subscriptions: Dict[str, set] = {}  # addr -> subscribed ports
        self._api_router = SerialAccessApiRouter(
            self._access_service,
            self._subscribe_api_port,
            self._unsubscribe_api_port,
        )
        self._log_router = SerialAccessLogRouter(
            lambda: self.log_dir,
            self._send_gui_message,
            self.error_occurred.emit,
        )
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # 当前可用的串口列表
        self._available_ports: List[str] = []

        # 设备信息缓存 {port: {"version": ..., "ip": ...}}
        self._device_info: Dict[str, dict] = {}

        # 数据缓冲区（每个串口一个）
        self._port_buffers: Dict[str, str] = {}  # port -> buffered_data
        self._last_flush_time: Dict[str, float] = {}  # port -> last_flush_timestamp
        self._buffer_lock = threading.Lock()

        # 启动缓冲区刷新线程
        self._flush_thread: Optional[threading.Thread] = None

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def client_count(self) -> int:
        return len(self._clients)

    @property
    def client_addresses(self) -> List[str]:
        with self._lock:
            return sorted(self._clients.keys())

    @property
    def client_port_labels(self) -> List[str]:
        with self._lock:
            labels = []
            for addr in sorted(self._clients.keys()):
                permission = self._client_permissions.get(addr, self.default_permission)
                open_ports = sorted(self._client_open_ports.get(addr, set()))
                labels.extend(f"{addr}:{port} [{permission}]" for port in open_ports)
            return labels

    @property
    def banned_ips(self) -> List[str]:
        with self._lock:
            return sorted(self._banned_ips)

    def client_infos(self) -> List[SerialAccessClientInfo]:
        with self._lock:
            infos = []
            for addr in sorted(self._clients.keys()):
                open_ports = sorted(self._client_open_ports.get(addr, set()))
                selected = self._client_selected_port.get(addr, "")
                infos.append(SerialAccessClientInfo(
                    address=addr,
                    ip=client_ip(addr),
                    permission=self._client_permissions.get(addr, self.default_permission),
                    authorized=self._client_authorized.get(addr, False),
                    opened_ports=open_ports,
                    selected_port=selected,
                    connected_at=self._client_connected_at.get(addr, time.time()),
                    last_active_at=self._client_last_active.get(addr, time.time()),
                    read_count=self._client_read_counts.get(addr, 0),
                    write_count=self._client_write_counts.get(addr, 0),
                ))
            return infos

    def set_client_permission(self, addr: str, permission: str) -> bool:
        permission = normalize_permission(permission)
        with self._lock:
            if addr not in self._clients:
                return False
            self._client_permissions[addr] = permission
            self._client_last_active[addr] = time.time()
        self.client_updated.emit(addr)
        return True

    def disconnect_client(self, addr: str) -> bool:
        with self._lock:
            exists = addr in self._clients
        if exists:
            self._remove_client(addr)
        return exists

    def ban_ip(self, ip: str, disconnect: bool = True) -> bool:
        if not ip:
            return False
        with self._lock:
            self._banned_ips.add(ip)
            targets = [
                addr for addr in self._clients.keys()
                if client_ip(addr) == ip
            ]
        if disconnect:
            for addr in targets:
                self._remove_client(addr)
        return True

    def unban_ip(self, ip: str) -> bool:
        with self._lock:
            if ip not in self._banned_ips:
                return False
            self._banned_ips.remove(ip)
            return True

    def update_port_list(self, ports: List[str]):
        """更新串口列表"""
        old_ports = set(self._available_ports)
        new_ports = set(ports)

        # 新增的串口
        added = new_ports - old_ports
        # 移除的串口
        removed = old_ports - new_ports

        self._available_ports = ports

        # 通知客户端
        for port in added:
            self._broadcast_message(MSG_TYPE_PORT_ADD, port, "")
        for port in removed:
            self._broadcast_message(MSG_TYPE_PORT_REMOVE, port, "")

    def broadcast_port_list(self):
        """广播完整串口列表给所有客户端"""
        msg = encode_message(MSG_TYPE_PORT_LIST, "", json.dumps(self._available_ports))
        dead_clients = []
        with self._lock:
            for addr, client in self._clients.items():
                if not self._client_authorized.get(addr, False):
                    continue
                try:
                    client.sendall(msg)
                except:
                    dead_clients.append(addr)
        for addr in dead_clients:
            self._remove_client(addr)

    def start(self):
        """启动服务器"""
        if self._running:
            print("[SerialAccessServer] Already running, skip start")
            return

        try:
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_socket.bind((self.host, self.port))
            self._server_socket.listen(5)
            self._server_socket.settimeout(1.0)

            self._running = True
            self._thread = threading.Thread(target=self._accept_loop, daemon=True)
            self._thread.start()

            # 启动缓冲区刷新线程
            self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
            self._flush_thread.start()

            print(f"[SerialAccessServer] Started on {self.host}:{self.port}")
        except Exception as e:
            print(f"[SerialAccessServer] Start failed: {e}")
            self.error_occurred.emit(f"服务器启动失败: {e}")

    def stop(self):
        """停止服务器"""
        self._running = False

        # 关闭所有客户端连接
        with self._lock:
            for addr, client in list(self._clients.items()):
                try:
                    client.close()
                except:
                    pass
            self._clients.clear()
            self._auth.clear()
            self._client_selected_port.clear()
            self._client_open_ports.clear()
            self._client_permissions.clear()
            self._client_connected_at.clear()
            self._client_last_active.clear()
            self._client_read_counts.clear()
            self._client_write_counts.clear()
            self._api_subscriptions.clear()

        # 清空缓冲区
        with self._buffer_lock:
            self._port_buffers.clear()
            self._last_flush_time.clear()
        self._output_buffer.clear()

        # 关闭服务器socket
        if self._server_socket:
            try:
                self._server_socket.close()
            except:
                pass
            self._server_socket = None

        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

        if self._flush_thread:
            self._flush_thread.join(timeout=2)
            self._flush_thread = None

    def send_to_port(self, port: str, data: str):
        """发送数据到指定串口的所有客户端（带缓冲）"""
        if not data:
            return

        flush_data = None

        # 将数据加入缓冲区
        with self._buffer_lock:
            if port not in self._port_buffers:
                self._port_buffers[port] = ""
                self._last_flush_time[port] = time.time()

            self._port_buffers[port] += data

            # 限制缓冲区大小，防止内存泄漏
            if len(self._port_buffers[port]) > 1024 * 1024:  # 1MB
                # 丢弃旧数据，保留最新的
                self._port_buffers[port] = self._port_buffers[port][-self.BUFFER_FLUSH_SIZE:]

            # 如果缓冲区超过阈值，立即刷新
            if len(self._port_buffers[port]) >= self.BUFFER_FLUSH_SIZE:
                flush_data = self._port_buffers[port]
                self._port_buffers[port] = ""
                self._last_flush_time[port] = time.time()

        # 在 buffer_lock 外发送数据，避免死锁
        if flush_data:
            self._send_port_data(port, flush_data)

    def on_serial_data(self, port: str, data: str):
        """Publish serial data to GUI remote clients and API subscribers."""
        self._output_buffer.append(port, data)
        self.send_to_port(port, data)
        event = {
            "id": 0,
            "event": "serial_data",
            "data": {"port": port, "content": data},
        }
        self._broadcast_api_to_subscribers(port, event)

    def on_port_state_changed(self, port: str, old_state: str, new_state: str, detail: str = ""):
        event = {
            "id": 0,
            "event": "port_state_changed",
            "data": {
                "port": port,
                "old_state": old_state,
                "new_state": new_state,
                "detail": detail,
            },
        }
        self._broadcast_api_to_all(event)

    def on_device_state_changed(self, port: str, old_state: str, new_state: str, detail: str = ""):
        event = {
            "id": 0,
            "event": "device_state_changed",
            "data": {
                "port": port,
                "old_state": old_state,
                "new_state": new_state,
                "detail": detail,
            },
        }
        self._broadcast_api_to_all(event)

    def _flush_loop(self):
        """定时刷新缓冲区的线程"""
        while self._running:
            time.sleep(self.CLIENT_REFRESH_INTERVAL)

            # 先获取需要刷新的数据（在 buffer_lock 内）
            flush_data = {}
            with self._buffer_lock:
                for port in list(self._port_buffers.keys()):
                    data = self._port_buffers.get(port, "")
                    if data:
                        flush_data[port] = data
                        self._port_buffers[port] = ""
                        self._last_flush_time[port] = time.time()

            # 然后发送数据（在 buffer_lock 外，避免死锁）
            for port, data in flush_data.items():
                self._send_port_data(port, data)

    def _flush_port_buffer(self, port: str):
        """刷新指定串口的缓冲区（需要在 _buffer_lock 内调用）"""
        data = self._port_buffers.get(port, "")
        if not data:
            return

        self._port_buffers[port] = ""
        self._last_flush_time[port] = time.time()

        # 注意：这里不能直接发送，因为在 _buffer_lock 内
        # 需要先释放 _buffer_lock 再获取 _lock，否则可能死锁
        # 所以这个方法只清空缓冲区，实际发送由调用者处理
        return data

    def _send_port_data(self, port: str, data: str):
        """发送数据到客户端（不持有 buffer_lock）"""
        if not data:
            return

        msg = encode_message(MSG_TYPE_DATA, port, data)

        dead_clients = []
        with self._lock:
            for addr, client in self._clients.items():
                if not self._client_authorized.get(addr, False):
                    continue
                # 只发送给选择了这个串口的客户端，或者没有选择的客户端（广播）
                selected = self._client_selected_port.get(addr, "")
                open_ports = self._client_open_ports.get(addr, set())
                if not selected or selected == port or port in open_ports:
                    try:
                        client.sendall(msg)
                    except:
                        dead_clients.append(addr)

        for addr in dead_clients:
            self._remove_client(addr)

    def _broadcast_message(self, msg_type: int, port: str, data: str):
        """广播消息给所有客户端"""
        msg = encode_message(msg_type, port, data)

        dead_clients = []
        with self._lock:
            for addr, client in self._clients.items():
                if not self._client_authorized.get(addr, False):
                    continue
                try:
                    client.sendall(msg)
                except:
                    dead_clients.append(addr)

        for addr in dead_clients:
            self._remove_client(addr)

    def rename_port(self, port: str, new_name: str):
        """通知客户端串口重命名"""
        self._broadcast_message(MSG_TYPE_PORT_RENAME, port, new_name)

    def broadcast_device_info(self, port: str, version: str, ip: str):
        """广播设备信息给所有客户端"""
        # 保存设备信息
        self._device_info[port] = {"version": version, "ip": ip}
        # 广播给所有客户端
        info = json.dumps({"version": version, "ip": ip})
        self._broadcast_message(MSG_TYPE_DEVICE_INFO, port, info)

    def _send_port_list(self, client_socket: socket.socket):
        """发送串口列表给客户端"""
        msg = encode_message(MSG_TYPE_PORT_LIST, "", json.dumps(self._available_ports))
        try:
            client_socket.sendall(msg)
        except:
            pass

    def _send_device_info(self, client_socket: socket.socket):
        """发送所有串口的设备信息给客户端"""
        for port, info in self._device_info.items():
            try:
                msg = encode_message(MSG_TYPE_DEVICE_INFO, port, json.dumps(info))
                client_socket.sendall(msg)
            except:
                pass

    def _accept_loop(self):
        """接受客户端连接的循环"""
        print("[SerialAccessServer] Accept loop started")
        while self._running:
            try:
                client_socket, addr = self._server_socket.accept()
                addr_str = f"{addr[0]}:{addr[1]}"
                print(f"[SerialAccessServer] Client connected: {addr_str}")

                with self._lock:
                    if addr[0] in self._banned_ips:
                        try:
                            client_socket.sendall(encode_message(MSG_TYPE_AUTH_RESULT, "", json.dumps({
                                "authenticated": False,
                                "required": False,
                                "reason": "banned",
                                "message": f"Remote access denied: IP {addr[0]} is banned",
                            })))
                            client_socket.close()
                        except Exception:
                            pass
                        self.error_occurred.emit(f"Client rejected: banned IP {addr[0]}")
                        continue
                    if len(self._clients) >= self.max_clients:
                        try:
                            client_socket.sendall(encode_message(MSG_TYPE_AUTH_RESULT, "", json.dumps({
                                "authenticated": False,
                                "required": False,
                                "reason": "max_clients",
                                "message": f"Remote access denied: max clients reached ({self.max_clients})",
                            })))
                            client_socket.close()
                        except Exception:
                            pass
                        self.error_occurred.emit(
                            f"Client rejected: max clients reached ({self.max_clients})"
                        )
                        continue
                    self._clients[addr_str] = client_socket
                    self._auth.add_client(addr_str)
                    now = time.time()
                    self._client_permissions[addr_str] = self.default_permission
                    self._client_connected_at[addr_str] = now
                    self._client_last_active[addr_str] = now
                    self._client_read_counts[addr_str] = 0
                    self._client_write_counts[addr_str] = 0

                if self.access_password:
                    client_socket.sendall(encode_message(MSG_TYPE_AUTH_RESULT, "", json.dumps({
                        "authenticated": False,
                        "required": True,
                    })))
                else:
                    # 发送当前串口列表
                    self._send_port_list(client_socket)

                    # 发送已有的设备信息
                    self._send_device_info(client_socket)

                self.client_connected.emit(addr_str)

                # 为每个客户端启动接收线程
                thread = threading.Thread(
                    target=self._client_receive_loop,
                    args=(client_socket, addr_str),
                    daemon=True
                )
                thread.start()

            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    print(f"[SerialAccessServer] Accept error: {e}")
                    self.error_occurred.emit(f"接受连接错误: {e}")

    def _client_receive_loop(self, client_socket: socket.socket, addr: str):
        client_socket.settimeout(1.0)
        buffer = b""

        while self._running and addr in self._clients:
            try:
                data = client_socket.recv(4096)
                if not data:
                    break

                buffer += data
                frames, buffer = extract_frames(buffer)

                for msg_data in frames:
                    try:
                        msg = decode_message(msg_data)
                        self._handle_client_message(addr, msg)
                    except Exception:
                        pass

            except socket.timeout:
                continue
            except Exception:
                break

        self._remove_client(addr)

    # 信号
    break_requested = pyqtSignal(str, str)  # 收到 break 请求 (client_addr, port)

    def _handle_client_message(self, addr: str, msg: dict):
        """处理客户端消息"""
        if "action" in msg:
            self._handle_api_message(addr, msg)
            return

        msg_type = msg.get("type", 0)
        port = msg.get("port", "")
        data = msg.get("data", "")

        if msg_type == MSG_TYPE_AUTH:
            self._handle_auth_message(addr, data)
            return

        if not self._is_authorized(addr):
            self.error_occurred.emit(f"未认证客户端请求已拒绝: {addr}")
            return

        if msg_type == MSG_TYPE_DATA:
            if not self._is_write_allowed(addr):
                self.error_occurred.emit(f"Write denied for read-only client: {addr}")
                return
            # 客户端发送的数据，转发到串口
            self._record_client_activity(addr, write=True)
            self.data_received.emit(addr, port, data)
        elif msg_type == MSG_TYPE_SELECT_PORT:
            # 客户端选择串口
            with self._lock:
                self._client_selected_port[addr] = port
                self._client_open_ports.setdefault(addr, set()).add(port)
                self._client_last_active[addr] = time.time()
            self.client_updated.emit(addr)
        elif msg_type == MSG_TYPE_UNSELECT_PORT:
            with self._lock:
                open_ports = self._client_open_ports.setdefault(addr, set())
                open_ports.discard(port)
                if not open_ports:
                    self._client_open_ports.pop(addr, None)
                if self._client_selected_port.get(addr) == port:
                    self._client_selected_port[addr] = next(iter(open_ports), "")
                self._client_last_active[addr] = time.time()
            self.client_updated.emit(addr)
        elif msg_type == MSG_TYPE_BREAK:
            if not self._is_write_allowed(addr):
                self.error_occurred.emit(f"Break denied for read-only client: {addr}")
                return
            # 客户端请求发送 Break 信号
            self._record_client_activity(addr, write=True)
            self.break_requested.emit(addr, port)
        elif msg_type == MSG_TYPE_LOG_LIST:
            # 客户端请求日志列表
            self._record_client_activity(addr, read=True)
            self._log_router.handle_list_request(addr)
        elif msg_type == MSG_TYPE_LOG_DOWNLOAD:
            # 客户端请求下载日志
            self._record_client_activity(addr, read=True)
            self._log_router.handle_download_request(addr, data)

    def _handle_auth_message(self, addr: str, data: str):
        with self._lock:
            authorized = self._auth.authenticate_payload(addr, data)
            client_socket = self._clients.get(addr)

        payload = {"authenticated": authorized}
        if not authorized:
            payload.update({
                "required": False,
                "reason": "bad_password",
                "message": "Remote access denied: invalid password",
            })
        self._send_gui_message(addr, MSG_TYPE_AUTH_RESULT, "", json.dumps(payload))

        if authorized and client_socket:
            with self._lock:
                self._client_last_active[addr] = time.time()
            self._send_port_list(client_socket)
            self._send_device_info(client_socket)
        elif not authorized:
            self.error_occurred.emit(f"客户端认证失败: {addr}")
            self._remove_client(addr)

    def _is_authorized(self, addr: str) -> bool:
        with self._lock:
            return self._auth.is_authorized(addr)

    def _is_write_allowed(self, addr: str) -> bool:
        with self._lock:
            return self._client_permissions.get(addr, self.default_permission) != PERMISSION_READ_ONLY

    def _record_client_activity(self, addr: str, read: bool = False, write: bool = False):
        with self._lock:
            if addr not in self._clients:
                return
            self._client_last_active[addr] = time.time()
            if read:
                self._client_read_counts[addr] = self._client_read_counts.get(addr, 0) + 1
            if write:
                self._client_write_counts[addr] = self._client_write_counts.get(addr, 0) + 1

    def _send_gui_message(self, addr: str, msg_type: int, port: str, data: str):
        msg = encode_message(msg_type, port, data)
        with self._lock:
            client = self._clients.get(addr)
        if not client:
            return
        try:
            client.sendall(msg)
        except Exception:
            self._remove_client(addr)

    def _handle_api_message(self, addr: str, msg: dict):
        request_id = msg.get("id", 0)
        action = msg.get("action", "")
        params = msg.get("params", {})

        if not self._is_authorized(addr):
            with self._lock:
                authenticated = self._auth.authenticate_params(addr, params)
            if not authenticated:
                self._send_api_message(addr, {
                    "id": request_id,
                    "code": ERR_BAD_PARAMS,
                    "message": "Authentication required",
                })
                return

        if action in WRITE_ACTIONS and not self._is_write_allowed(addr):
            self._send_api_message(addr, {
                "id": request_id,
                "code": ERR_BAD_PARAMS,
                "message": "Write denied: client is read-only",
            })
            return

        try:
            result = self._api_router.dispatch(addr, action, params)
        except Exception as exc:
            result = {"code": ERR_INTERNAL, "message": str(exc)}

        self._record_client_activity(addr, write=action in WRITE_ACTIONS, read=action not in WRITE_ACTIONS)
        response = {"id": request_id, **result}
        self._send_api_message(addr, response)

    def _subscribe_api_port(self, addr: str, port: str):
        with self._lock:
            self._api_subscriptions.setdefault(addr, set()).add(port)

    def _unsubscribe_api_port(self, addr: str, port: str):
        with self._lock:
            self._api_subscriptions.setdefault(addr, set()).discard(port)

    def _send_api_message(self, addr: str, message: dict):
        data = encode_service_message(message)
        with self._lock:
            client = self._clients.get(addr)
        if not client:
            return
        try:
            client.sendall(data)
        except Exception:
            self._remove_client(addr)

    def _broadcast_api_to_subscribers(self, port: str, event: dict):
        data = encode_service_message(event)
        with self._lock:
            targets = [
                (addr, client)
                for addr, client in self._clients.items()
                if self._client_authorized.get(addr, False)
                and port in self._api_subscriptions.get(addr, set())
            ]
        self._send_api_payload_to_targets(targets, data)

    def _broadcast_api_to_all(self, event: dict):
        data = encode_service_message(event)
        with self._lock:
            targets = [
                (addr, client)
                for addr, client in self._clients.items()
                if self._client_authorized.get(addr, False)
            ]
        self._send_api_payload_to_targets(targets, data)

    def _send_api_payload_to_targets(self, targets, data: bytes):
        dead_clients = []
        for addr, client in targets:
            try:
                client.sendall(data)
            except Exception:
                dead_clients.append(addr)
        for addr in dead_clients:
            self._remove_client(addr)

    def _remove_client(self, addr: str):
        """移除客户端"""
        with self._lock:
            if addr in self._clients:
                try:
                    self._clients[addr].close()
                except:
                    pass
                del self._clients[addr]
            self._auth.remove_client(addr)
            if addr in self._client_selected_port:
                del self._client_selected_port[addr]
            if addr in self._client_open_ports:
                del self._client_open_ports[addr]
            if addr in self._client_permissions:
                del self._client_permissions[addr]
            if addr in self._client_connected_at:
                del self._client_connected_at[addr]
            if addr in self._client_last_active:
                del self._client_last_active[addr]
            if addr in self._client_read_counts:
                del self._client_read_counts[addr]
            if addr in self._client_write_counts:
                del self._client_write_counts[addr]
            if addr in self._api_subscriptions:
                del self._api_subscriptions[addr]
        self.client_disconnected.emit(addr)
