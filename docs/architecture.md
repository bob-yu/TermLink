# Architecture

## Overview

TermLink is a PyQt5 desktop application with a layered structure:

| Layer | Path | Responsibility |
|---|---|---|
| Entry point | `main.py` | Creates `QApplication`, applies app identity, and opens the main window. |
| UI | `ui/` | Main window, dialogs, widgets, icons, and UI controllers. |
| Core | `core/` | Serial workers, SSH/Telnet workers, remote serial access, logging, terminal logic, and automation services. |
| Utilities | `utils/` | Configuration schema/codec, config manager, and documentation builder. |
| Automation | `automation/` | CLI and MCP adapters for external tools. |
| Tests | `tests/` | Unit tests for configuration, controllers, protocol, sessions, and terminal behavior. |

## Main Window Responsibilities

`ui/main_window.py` owns the application shell:

- Toolbar, status bar, docks, and tab container.
- Session registry.
- Top-level action wiring.
- Delegation to controllers.
- High-level signal routing between workers and UI.

The main window should not accumulate detailed business logic when a controller or core service can own it.

## UI Controllers

| Controller | Responsibility |
|---|---|
| `LocalSerialSessionController` | Creates local serial workers, tabs, tooltips, and worker signal connections. |
| `RemoteSerialSessionController` | Creates remote serial tabs, routes remote data by server and port, and closes unused remote clients. |
| `SerialAccessController` | Starts/stops the local Serial Access server, connects remote clients, and opens access settings. |
| `NetworkTerminalSessionController` | Creates SSH/Telnet workers and tabs. |
| `RemoteLogDownloadController` | Displays remote logs and downloads selected files. |
| `SessionController` | Connect/disconnect operations across sessions. |
| `TerminalSettingsController` | Terminal and logging settings. |
| `ScanPatternSettingsController` | Linux serial scan pattern settings. |

## Session Model

All open sessions are stored in:

```python
self._sessions: Dict[str, tuple]
```

Key formats:

| Session type | Example key |
|---|---|
| Local serial | `COM12` or `/dev/ttyUSB0` |
| Remote serial | `remote://127.0.0.1:56337/COM12` |
| SSH/Telnet | Scheme-based network session key |

Remote session keys include the server address so the same port name can exist on multiple remote servers.

## Serial Configuration

`PortConfigData` stores serial line settings:

| Field | Example |
|---|---|
| `baudrate` | `115200` |
| `data_bits` | `8` |
| `parity` | `N` |
| `stop_bits` | `1.0` |
| `flow_control` | `none` |

These fields are converted into `SerialConfig` and passed to `pyserial`.

Flow control values:

| Value | pyserial flag |
|---|---|
| `none` | all flow control disabled |
| `xonxoff` | `xonxoff=True` |
| `rtscts` | `rtscts=True` |
| `dsrdtr` | `dsrdtr=True` |

## Serial Access Service

Remote serial access uses one unified service:

| Module | Responsibility |
|---|---|
| `serial_access_server.py` | TCP server, client state, authentication, permissions, and message routing. |
| `serial_access_client.py` | GUI client for remote serial servers. |
| `serial_access_service.py` | Action-oriented API surface for automation. |
| `serial_access_api_router.py` | Routes automation actions. |
| `serial_access_log_router.py` | Serves remote log lists and file blocks. |
| `serial_access_permissions.py` | Client permission data. |
| `serial_output_buffer.py` | Per-port ring buffer used by CLI/MCP reads. |
| `remote_server_manager.py` | Tracks multiple GUI remote server clients. |

The old dual-port design has been removed. GUI remote access, CLI, and MCP share the same Serial Access server port.

## Multi-Server Remote Client Model

The GUI can connect to multiple remote Serial Access servers at the same time.

`RemoteServerManager` maps normalized server ids to `SerialAccessClient` objects:

```text
127.0.0.1:56337 -> SerialAccessClient
192.168.1.20:56337 -> SerialAccessClient
```

Remote tabs are keyed by server and port:

```text
remote://127.0.0.1:56337/COM12
remote://192.168.1.20:56337/COM12
```

This avoids collisions when different servers expose the same port name.

## Logging

Local session logs are written by worker-owned `SerialLogger` instances. Runtime UI diagnostics are separate and shown in the Runtime Log panel.

Remote log download is handled through the Serial Access connection. The client asks for a log list and downloads a selected file in chunks.

## Configuration

Configuration is handled by:

- `utils/config_schema.py`
- `utils/config_codec.py`
- `utils/config_manager.py`

The codec supports legacy fields when loading, but writes the current schema.

`config.example.json` is the tracked default template. Runtime state is written to local `config.json`, which is ignored by git so machine-specific ports, passwords, window geometry, dock state, command sets, and highlight rules do not enter commits or release templates.

Important remote access fields:

| Field | Purpose |
|---|---|
| `serial_access_mode` | `disabled`, `server`, or legacy-compatible client state. |
| `serial_access_host` | Server bind address. |
| `serial_access_port` | Unified Serial Access port. |
| `serial_access_password` | Password required when this instance acts as server. |
| `serial_access_client_password` | Last client-side password used for Add Remote. |
| `serial_access_max_clients` | Max connected clients. |
| `serial_access_default_permission` | Default permission for new clients. |
| `serial_access_banned_ips` | Persisted banned IP list. |

## Documentation Generation

`utils/docs_builder.py` converts selected Markdown files in `docs/` to `docs/html/`.

The Documentation toolbar action opens:

```text
docs/html/index.html
```

## Test Strategy

Tests cover:

- Config load/save compatibility.
- Serial Access protocol and authentication.
- Remote session key behavior.
- Multi-server remote session routing.
- UI controller orchestration.
- Terminal search, selection, and key mapping.
- Logging and remote log download.

The test suite uses stubs for GUI-heavy or environment-specific code where direct device access is not practical.
