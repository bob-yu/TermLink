# Troubleshooting

## Serial Port Does Not Connect

Check:

- The port is not already opened by another application.
- Baudrate and line settings match the device.
- USB adapter drivers are installed.
- The selected port name is correct.
- Flow control is set to `None` unless the device requires it.

Common embedded console setting:

```text
115200 8N1, no flow control
```

## No Output in Terminal

Check:

- The session is connected.
- The device is powered.
- TX/RX wiring is correct.
- Baudrate is correct.
- You are scrolled to the bottom.
- The device actually emits output.

If text is garbled, the baudrate or line settings are usually wrong.

## Cannot Add Remote Serial

Check:

- Server address and port are correct.
- Server is running.
- Password is correct.
- Your IP is not banned.
- Server has not reached the max client limit.
- Firewall allows the Serial Access port.

For local loopback testing, use:

```text
127.0.0.1:56337
```

Do not use `0.0.0.0` as a client target unless the UI normalizes it. `0.0.0.0` is a bind address, not a remote destination.

## Remote Port Opens but Does Not Respond

Check:

- The server-side local serial session is connected.
- The remote client has read-write permission.
- The selected remote tab maps to the expected server and port.
- Another client is not sending conflicting input.
- The server did not disconnect or ban the client.

## CLI or MCP Cannot Write

Check the client permission in `Serial Remote Access Control`.

Read-only clients can list, watch, and read logs, but cannot:

- write
- command
- break

## CLI or MCP Watch Missed Output

The ring buffer is finite. If a client waits too long before reading, old output may be overwritten.

When this happens, the response reports:

```json
{"lost": true}
```

Continue from the returned `end_seq`.

## Documentation Does Not Open

Check:

- `docs/html/index.html` exists.
- `utils.docs_builder` can regenerate the HTML files.
- The packaged app includes the `docs` directory.

Regenerate docs from source:

```bash
python -m utils.docs_builder
```

## Packaged App Uses Old Name

After renaming or changing package metadata:

1. Clean old build outputs.
2. Rebuild with `TermLink.spec`.
3. Ensure `run.bat` points to `TermLink.exe`.

Commands:

```bat
clean.bat
build.bat
```
