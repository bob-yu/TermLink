# TermLink Documentation

TermLink is a desktop terminal tool for local serial ports, remote serial access, SSH/Telnet sessions, runtime logs, command sets, and automation integrations.

The application is designed for embedded development, hardware bring-up, production debugging, and remote device access. It starts with no serial ports opened. Users explicitly scan, add, and connect the sessions they need.

## Documentation Map

| Document | Purpose |
|---|---|
| [User Guide](user-guide.html) | Daily workflows for local serial, SSH/Telnet, remote serial, logs, and command sets. |
| [Architecture](architecture.html) | Code structure, core modules, configuration model, and test strategy. |
| [Remote Access](remote-access.html) | Remote serial server/client behavior, permissions, connected clients, and multi-server usage. |
| [Automation Interfaces](automation.html) | CLI and MCP interfaces exposed by the Serial Access API. |
| [Logging](logging.html) | Local logs, remote log download, retention, and troubleshooting. |
| [Troubleshooting](troubleshooting.html) | Common connection, display, remote access, and packaging issues. |

## Core Capabilities

- Local serial sessions with baudrate, data bits, parity, stop bits, and flow control.
- Batch serial scan and add workflow.
- SSH and Telnet terminal sessions.
- Remote serial access over a single Serial Access service port.
- Multiple remote servers connected from one client instance.
- Password-protected remote access with client control and IP bans.
- Runtime log panel, per-session logs, and remote server log download.
- Command sets for frequently used manual commands.
- CLI and MCP adapters for automation and AI-assisted workflows.

## Recommended First Run

1. Start TermLink.
2. Use `Scan Ports` to select one or more serial ports.
3. Set serial line parameters in the same scan dialog.
4. Add the selected ports.
5. Connect only the ports you want to use.
6. Open `More > Runtime Log` when diagnosing tool behavior.
7. Open `Settings > Serial Remote Access Settings` only when sharing local serial ports to other clients.

## Design Principles

- No automatic opening of all serial ports on startup.
- One unified Serial Access service for GUI remote terminals, CLI, and MCP.
- Remote access must be explicit and password-protected.
- Local UI state is remembered as a user preference.
- GUI workflows should stay focused on connection management, not hidden automation.
