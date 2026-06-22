# Remote Access

Remote Access lets one TermLink instance expose local serial ports to other TermLink clients, CLI clients, and MCP clients.

## Concepts

| Term | Meaning |
|---|---|
| Server | The TermLink instance physically connected to serial devices. |
| Client | A GUI, CLI, or MCP client connecting to the server. |
| Local serial | A serial port opened on the server machine. |
| Remote serial | A client-side terminal tab mapped to a server-side local serial port. |
| Proxy client | A client currently connected to this machine's Serial Access server. |

## Server Workflow

1. Open `Settings > Serial Remote Access Settings`.
2. Enable the server.
3. Set listen host and port.
4. Set the access password.
5. Set max clients and default permission.
6. Add and connect the local serial ports you want to expose.

The server does not automatically scan, add, or connect every serial port. This avoids accidentally occupying devices.

## Client Workflow

1. Click `Add Connection > Remote Serial`.
2. Enter server address, for example:

```text
192.168.1.20:56337
```

3. Enter the server password.
4. Select one or more remote ports from the returned list.
5. TermLink creates remote serial tabs for the selected ports.

If a selected port is already opened for that server, it is shown as opened and cannot be added again.

## Multiple Remote Servers

One TermLink client can connect to multiple remote servers at the same time.

The Connections panel groups remote ports by server:

```text
Remote
  127.0.0.1:56337
    COM12 [Connected]
    COM5 [Disconnected]
  192.168.1.20:56337
    ttyUSB0 [Connected]
```

The internal session key includes both server and port:

```text
remote://127.0.0.1:56337/COM12
```

This prevents collisions when different servers expose the same port name.

## Access Control

Open:

```text
Settings > Serial Remote Access Control
```

Use this panel to:

- View connected clients.
- Disconnect a client.
- Ban an IP address.
- Unban an IP address.
- Set a client to read-only.
- Set a client to read-write.

Access control applies to GUI remote clients, CLI clients, and MCP clients.

## Passwords

There are two password fields with different roles:

| Field | Meaning |
|---|---|
| Server access password | Password required when this TermLink instance acts as server. |
| Remote Serial password | Password this TermLink instance uses when connecting to another server. |

Changing the server password should not automatically change the client password.

## Permissions

| Permission | Allowed |
|---|---|
| Read-only | list, state, watch, log, GUI receive |
| Read-write | read operations plus write, command, break, GUI input |

If a client is banned or disconnected by the server, the GUI should show a connection error instead of silently removing the session.

## Firewall Notes

The server listens on one TCP port. The default is:

```text
56337
```

Windows example:

```powershell
netsh advfirewall firewall add rule name="TermLink" dir=in action=allow protocol=tcp localport=56337
```

Linux example:

```bash
sudo ufw allow 56337/tcp
```

## Data Flow

```text
Client terminal input
  -> SerialAccessClient
  -> TCP connection
  -> SerialAccessServer
  -> Local SerialWorker
  -> Physical serial device

Physical serial output
  -> Local SerialWorker
  -> SerialAccessServer
  -> GUI remote terminals
  -> CLI/MCP ring-buffer reads
```

GUI remote terminals receive realtime pushed data. CLI and MCP read from the server-side ring buffer.
