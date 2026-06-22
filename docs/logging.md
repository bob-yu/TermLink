# Logging

TermLink has three logging-related surfaces:

- Per-session serial/network logs.
- Runtime Log panel for tool diagnostics.
- Remote server log download.

## Session Logs

Each local serial session can write output to its own log file.

Log behavior is configured in terminal settings:

| Setting | Purpose |
|---|---|
| Log directory | Where log files are stored. |
| Enable logging | Turns session logging on or off. |
| Timestamp output | Adds timestamps to log lines. |
| Log file naming pattern | Controls generated log file names. |
| Retention limits | Limits log age, total size, and file size. |

Remote serial tabs display remote output, but server-side physical serial logs are owned by the server instance.

## Runtime Log Panel

The Runtime Log panel is a UI diagnostics surface. It is hidden by default.

Open it with:

```text
More > Runtime Log
```

Use it to inspect tool events while developing or troubleshooting.

Runtime logs are different from serial session logs. They describe TermLink behavior rather than device output.

## Remote Log Download

When connected to a remote server, a client can request the server log list and download selected log files.

Typical flow:

1. Connect to a remote Serial Access server.
2. Open the remote log download action.
3. Refresh the log list.
4. Select a log file.
5. Download it to a local path.

If the action is unavailable, check that a remote client connection exists.

## Log Cleanup

Log cleanup is managed by the log manager according to configured limits:

- Maximum age in days.
- Maximum total log directory size.
- Maximum individual file size.
- Auto-clean enabled or disabled.

Cleanup runs asynchronously so startup is not blocked by log maintenance.

## Troubleshooting Logs

If logs are missing:

- Confirm logging is enabled.
- Confirm the log directory exists and is writable.
- Confirm the session is connected and receiving data.
- Check whether cleanup limits removed older files.

If remote log download fails:

- Confirm the client is still connected to the server.
- Confirm access is not banned or disconnected.
- Confirm the server log directory exists.
- Confirm the selected file has not been removed during cleanup.
