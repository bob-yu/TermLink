# Automation Interfaces

TermLink exposes local serial sessions through the Serial Access API. The GUI remote terminal, CLI, and MCP adapter share the same server, authentication rules, permissions, and ring-buffer based read model.

## When to Use Automation

Use CLI or MCP when an external tool needs to:

- List available local serial ports exposed by a TermLink server.
- Read current port state.
- Send data or commands to a serial port.
- Wait for expected output.
- Read recent serial logs.
- Locate a device by IP.
- Integrate serial workflows into scripts, CI jobs, or AI-assisted tools.

## Server Requirements

Automation uses the same Serial Access server as GUI remote serial access.

1. Open `Settings > Serial Remote Access Settings`.
2. Enable the server.
3. Choose host and port.
4. Set a password when needed.
5. Add and connect local serial ports manually.

The default port is:

```text
56337
```

The old `9527` / `9528` split-port design is no longer used.

## Authentication and Permissions

The Serial Access server enforces the same access rules for GUI, CLI, and MCP clients:

| Rule | Effect |
|---|---|
| Password mismatch | Connection is rejected. |
| Banned IP | Connection is rejected. |
| Max clients reached | Connection is rejected. |
| Read-only permission | Read operations are allowed; write, command, and break operations are rejected. |
| Read-write permission | Read and write operations are allowed. |

Permissions can be changed from `Serial Remote Access Control`.

## CLI

Run the CLI module:

```bash
python -m automation.serialtool --host 127.0.0.1 --port 56337 list
```

If the server requires a password:

```bash
python -m automation.serialtool --host 127.0.0.1 --port 56337 --password secret list
```

### Common Commands

List ports:

```bash
python -m automation.serialtool --host 127.0.0.1 --port 56337 list
```

Get state:

```bash
python -m automation.serialtool --host 127.0.0.1 --port 56337 state COM12
```

Write raw data:

```bash
python -m automation.serialtool --host 127.0.0.1 --port 56337 write COM12 "reboot\r"
```

Send a command and wait:

```bash
python -m automation.serialtool --host 127.0.0.1 --port 56337 command COM12 "cat /system/bin/version" --duration 5 --expect "#" --idle-timeout 0.3
```

Watch output:

```bash
python -m automation.serialtool --host 127.0.0.1 --port 56337 watch COM12 --duration 2 --expect "#" --idle-timeout 0.3
```

Read the current ring-buffer state:

```bash
python -m automation.serialtool --host 127.0.0.1 --port 56337 buffer-state COM12
```

Read log snapshot:

```bash
python -m automation.serialtool --host 127.0.0.1 --port 56337 log COM12 --lines 100
```

Interactive console:

```bash
python -m automation.serialtool --host 127.0.0.1 --port 56337 console COM12
```

### CLI Command Reference

| Command | Purpose |
|---|---|
| `list` | List exposed serial ports. |
| `state <port>` | Read current device/session state. |
| `find-ip <ip>` | Find a serial port by detected device IP. |
| `write <port> <data>` | Write raw data. |
| `watch <port>` | Read buffered output with bounded wait conditions. |
| `buffer-state <port>` | Read ring-buffer size, cursor, and drop counters. |
| `command <port> <command>` | Send a command, then watch for output. |
| `break <port>` | Send serial break. |
| `log <port>` | Read recent log lines. |
| `fetch-device-ip <port>` | Trigger device IP discovery. |
| `console <port>` | Interactive long-running console mode. |
| `request <action> --params JSON` | Low-level action request. |

Legacy command aliases such as `list-ports`, `get-port-state`, `write-data`, `send-command`, `send-break`, and `get-log-snapshot` are still accepted.

## Watch and Command Semantics

`watch` and `command` return when the first condition is met:

- `expect` is found in collected output.
- `idle_timeout` seconds pass after at least one byte has been received.
- `duration` seconds pass.

Example:

```bash
python -m automation.serialtool watch COM12 --duration 10 --expect "login:" --idle-timeout 0.5
```

### Watch Start Position

`watch` accepts a `--from` option:

| Value | Meaning |
|---|---|
| `latest` | Start from the current latest sequence. This is the default and waits for new output only. |
| `oldest` | Start from the oldest data currently retained in the ring buffer. |
| `seq` | Start after the provided `--start-seq` value. |

Examples:

```bash
python -m automation.serialtool watch COM12 --from latest --duration 5
python -m automation.serialtool watch COM12 --from oldest --duration 1
python -m automation.serialtool watch COM12 --from seq --start-seq 1200 --duration 5
```

Use `latest` for realtime monitoring, `oldest` to inspect the retained buffer,
and `seq` for incremental polling.

The response includes cursor metadata:

| Field | Meaning |
|---|---|
| `start_seq` | Sequence number used as the read start point. |
| `end_seq` | Sequence number after the returned data. |
| `latest_seq` | Latest sequence currently known by the server. |
| `lost` | `true` if the requested start point was overwritten by the ring buffer. |

The ring buffer is not a queue. Reads do not consume data. Multiple clients can read the same serial output independently by storing their own `end_seq` and passing it as the next `start_seq`.

### Buffer State

`buffer-state` reports the server-side ring buffer for one serial port:

```bash
python -m automation.serialtool buffer-state COM12
```

Typical response:

```json
{
  "port": "COM12",
  "current_bytes": 140,
  "max_bytes": 10485760,
  "oldest_seq": 1,
  "latest_seq": 4,
  "dropped_bytes": 0,
  "dropped_chunks": 0,
  "last_drop_time": 0
}
```

Use `oldest_seq` and `latest_seq` to decide whether a saved cursor is still in
range. If `saved_seq < oldest_seq - 1`, the next `watch --from seq` will report
`lost=true`.

## MCP

Configure your MCP client to start the MCP stdio adapter:

```bash
python -m automation.mcp_server --host 127.0.0.1 --port 56337
```

With password:

```bash
python -m automation.mcp_server --host 127.0.0.1 --port 56337 --password secret
```

### MCP Tools

| Tool | Purpose |
|---|---|
| `serial_list` | List exposed serial ports. |
| `serial_state` | Read current port state. |
| `serial_find_ip` | Find a port by IP. |
| `serial_write` | Write raw data. |
| `serial_watch` | Read buffered output with bounded wait conditions. |
| `serial_buffer_state` | Read ring-buffer size, cursor, and drop counters. |
| `serial_command` | Send command and collect output. |
| `serial_break` | Send serial break. |
| `serial_log` | Read recent log lines. |
| `serial_fetch_device_ip` | Trigger IP discovery. |

MCP tool calls are request/response operations. They do not hold an infinite stream open. Use `duration`, `expect`, and `idle_timeout` to bound each read operation.

`serial_watch` accepts the same cursor controls as CLI:

```json
{
  "port": "COM12",
  "from": "seq",
  "start_seq": 1200,
  "duration": 5,
  "idle_timeout": 0.5
}
```

Valid `from` values are `latest`, `oldest`, and `seq`.

## GUI Remote Terminal vs CLI/MCP

| Consumer | Read model |
|---|---|
| GUI remote terminal | Realtime push connection. |
| CLI `watch` / `command` | Bounded ring-buffer read. |
| MCP `serial_watch` / `serial_command` | Bounded ring-buffer read. |

All consumers observe the same serial output. Reading through CLI or MCP does not consume data from the GUI, and the GUI does not consume data from CLI or MCP.

## Practical Patterns

### Send Command and Continue From Cursor

1. Call `serial_command`.
2. Store `end_seq`.
3. Call `serial_watch` later with `start_seq=end_seq`.

This avoids rereading old output while still allowing multiple clients to read independently.

### Handle Buffer Loss

If `lost` is `true`, the requested `start_seq` is too old. The server has overwritten that portion of the ring buffer. The client should treat the returned data as a resynchronization point and continue from the returned `end_seq`.
