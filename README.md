# TermLink

TermLink is a desktop terminal tool for local serial ports, remote serial access, SSH/Telnet sessions, command sets, logs, and automation integrations.

It is built with Python and PyQt5. The application is intended for embedded development, hardware bring-up, production debugging, and remote device access.

## Highlights

- Local serial terminals with baudrate, data bits, parity, stop bits, and flow control.
- Batch scan and add workflow for multiple serial ports.
- SSH and Telnet terminal sessions.
- Remote serial access through one Serial Access service port.
- Multiple remote servers connected from one GUI client.
- Password-protected access, max client limits, read-only/read-write permissions, and IP bans.
- Runtime log panel, per-session logs, and remote server log download.
- Named command sets for repeated manual commands.
- CLI and MCP adapters for automation and AI-assisted workflows.

## Quick Start

Install dependencies:

```bash
pip install -r requirements.txt
```

Run from source:

```bash
python main.py
```

Run on Windows through the helper script:

```bat
run.bat
```

TermLink does not automatically open all serial ports at startup. Use `Scan Ports` or `Add Connection > Serial`, then connect only the sessions you need.

## Project Layout

```text
TermLink/
  main.py                 Application entry point
  config.example.json     Tracked default configuration template
  requirements.txt        Python dependencies
  run.bat                 Windows source/portable launcher
  build.bat               Windows portable package helper
  build.py                Cross-platform PyInstaller helper
  build.sh                Linux tar.gz/deb packaging helper
  clean.bat               Local build/log cleanup helper
  TermLink.spec           PyInstaller spec

  core/                   Serial, SSH/Telnet, remote access, logging, protocol, and terminal core
  ui/                     PyQt windows, dialogs, widgets, icons, and controllers
  utils/                  Configuration and documentation utilities
  automation/             CLI and MCP adapters
  tests/                  Unit tests
  docs/                   Markdown and generated HTML documentation
  assets/                 Application icon assets and icon design sources
  tools/                  Developer tools
```

Generated local files and folders such as `config.json`, `logs/`, `portable/`, `build/`, and `dist/` are ignored by git.

## Documentation

Source documentation is in `docs/`.

Generated HTML documentation is in `docs/html/` and can be opened from the TermLink toolbar.

Main documents:

- `docs/index.md`
- `docs/user-guide.md`
- `docs/architecture.md`
- `docs/remote-access.md`
- `docs/automation.md`
- `docs/logging.md`
- `docs/troubleshooting.md`

Regenerate HTML documentation:

```bash
python -m utils.docs_builder
```

or:

```bash
python build_docs.py
```

## Serial Workflow

1. Click `Scan Ports`.
2. Select one or more ports.
3. Set baudrate, data bits, parity, stop bits, and flow control.
4. Add the selected ports.
5. Connect manually when ready.

Common default:

```text
115200 8N1, no flow control
```

## Remote Serial Access

Remote access uses one Serial Access server port. The default is:

```text
56337
```

Server workflow:

1. Open `Settings > Serial Remote Access Settings`.
2. Enable the server.
3. Set host, port, password, max clients, and default permission.
4. Add and connect local serial ports.

Client workflow:

1. Click `Add Connection > Remote Serial`.
2. Enter `host:port` and password.
3. Select one or more exposed remote ports.

Remote GUI clients, CLI, and MCP use the same server and access rules.

## Automation

CLI example:

```bash
python -m automation.serialtool --host 127.0.0.1 --port 56337 list
python -m automation.serialtool --host 127.0.0.1 --port 56337 command COM12 "cat /system/bin/version" --duration 5 --expect "#" --idle-timeout 0.3
```

MCP stdio adapter:

```bash
python -m automation.mcp_server --host 127.0.0.1 --port 56337
```

See `docs/automation.md` for the full CLI and MCP reference.

## Build

Windows portable package:

```bat
build.bat
```

Build script roles:

- `build.bat`: Windows portable package workflow. Reuses `dist/` or an installed package when possible, otherwise builds with `TermLink.spec`.
- `build.py`: Cross-platform Python helper for PyInstaller directory or one-file builds.
- `build.sh`: Linux shell workflow for directory builds, one-file builds, tar.gz release packages, and `.deb` packages.

PyInstaller directly:

```bash
python -m PyInstaller --noconfirm TermLink.spec
```

Python helper:

```bash
python build.py
python build.py onefile
```

## Test

Run the full test suite:

```bash
python -m unittest discover -s tests
```

Compile check:

```bash
python -m compileall -q main.py core ui utils automation tools tests
```

## Platform Notes

| Platform | Serial examples |
|---|---|
| Windows | `COM1`, `COM12` |
| Linux | `/dev/ttyUSB0`, `/dev/ttyACM0`, `/dev/ttyS0` |
| macOS | `/dev/tty.usbserial-*`, `/dev/tty.usbmodem*` |

Linux serial permissions:

```bash
sudo usermod -a -G dialout "$USER"
```

Log out and back in after changing group membership.

## License

MIT License.
