# User Guide

## Start TermLink

Run from source:

```bash
python main.py
```

Or use the packaged executable:

```bash
TermLink.exe
```

TermLink does not automatically open serial ports. Add and connect sessions manually.

## Main Window

| Area | Purpose |
|---|---|
| Toolbar | Scan ports, add connections, connect/disconnect sessions, open settings, and open documentation. |
| Connections panel | Shows local serial sessions, remote serial sessions grouped by server, SSH/Telnet sessions, and remote clients connected to this machine. |
| Tab area | One terminal tab per local serial, remote serial, SSH, or Telnet session. |
| Runtime Log panel | Optional diagnostic log panel for tool behavior during development and troubleshooting. |
| Command Sets panel | Optional panel for named groups of reusable commands. |
| Status bar | Shows connection counts and remote access status. |

## Add Local Serial Ports

### Scan and Add Multiple Ports

1. Click `Scan Ports`.
2. Select the ports to add.
3. Set serial line parameters in the same dialog:
   - Baudrate
   - Data bits
   - Parity
   - Stop bits
   - Flow control
4. Click `OK`.
5. Connect the added sessions manually.

The common default is `115200 8N1` with no flow control.

### Add One Port Manually

1. Click `Add Connection > Serial`.
2. Enter or select the serial port.
3. Set baudrate, data bits, parity, stop bits, and flow control.
4. Click `OK`.
5. Connect the tab when ready.

The Add Serial dialog intentionally does not expose login, auto command, or keyword automation. Those features are internal/advanced behavior and are not part of the normal connection workflow.

## SSH and Telnet

1. Click `Add Connection`.
2. Select `SSH` or `Telnet`.
3. Enter host, port, and credentials when needed.
4. Create the session.

SSH/Telnet sessions appear in the same tab area and Connections panel as serial sessions.

## Terminal Operation

| Action | Behavior |
|---|---|
| Type in terminal | Sends input to the selected session. |
| Right-click | Opens terminal actions such as copy, paste, find, clear, and break. |
| Drag selection | Selects terminal text. |
| `Ctrl+F` | Opens find. |
| `F3` / `Shift+F3` | Find next / previous. |
| `Ctrl+End` | Scroll to bottom. |
| `Shift+PageUp` / `Shift+PageDown` | Scroll terminal history. |

## Connection Panel

Single-click a session to switch to its tab.

Double-click a disconnected session to connect it.

Remote sessions are grouped by server:

```text
Remote
  127.0.0.1:56337
    COM12 [Connected]
  192.168.1.20:56337
    COM5 [Disconnected]
```

`Proxy Clients` shows clients connected to this machine when local Remote Access server mode is enabled.

## Command Sets

Command Sets are named groups of commands. They are useful for repeated manual workflows such as collecting version information or checking network state.

1. Open `More > Command Sets`.
2. Add a command set with a name and commands.
3. Select a connected terminal tab.
4. Run the command set.

Command Sets do not replace automation APIs. They are a UI convenience for humans.

## Runtime Log Panel

The Runtime Log panel is hidden by default.

Open it with:

```text
More > Runtime Log
```

Use it when diagnosing connection behavior, remote access errors, or UI state issues.

## User Preferences

TermLink automatically saves user preferences such as:

- Window size and position.
- Dock visibility.
- Command Sets panel width.

These preferences are stored in the configuration file. They should not be confused with project defaults.

TermLink creates a local `config.json` when needed. The project default template is `config.example.json`; normal user preferences and local remote-access passwords are kept out of the repository.
