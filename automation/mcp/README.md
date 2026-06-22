# TermLink MCP Adapter

The MCP adapter in `automation/mcp_server.py` is a dependency-free JSON-RPC
stdio bridge over `automation.serial_access_client.SerialAccessApiClient`.

Recommended tools:

- `serial_list`
- `serial_state`
- `serial_find_ip`
- `serial_write`
- `serial_watch`
- `serial_buffer_state`
- `serial_command`
- `serial_break`
- `serial_log`
- `serial_fetch_device_ip`

`serial_watch` is the bounded read interface. It accepts `duration`, `expect`,
`idle_timeout`, `from`, `start_seq`, and `regex`.

Valid `from` values:

- `latest`: wait for new output only. This is the default.
- `oldest`: read from the oldest data retained in the ring buffer.
- `seq`: read after the provided `start_seq`.

Multiple MCP clients can read the same serial port independently by preserving
their own returned `end_seq` cursor.

`serial_buffer_state` reports `current_bytes`, `max_bytes`, `oldest_seq`,
`latest_seq`, `dropped_bytes`, `dropped_chunks`, and `last_drop_time` for a port.

Run it with:

```bash
python -m automation.mcp_server --host 127.0.0.1 --port 56337 --password secret
```

