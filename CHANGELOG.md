# Changelog

## v1.0.5 (2026-03-18)

### New

- Added log lifecycle management through `LogManager`, including retention by age, total size limits, per-file size limits, rotation, and cleanup of stale empty logs.
- Added configurable log filename templates with variables such as `{port}`, `{date}`, `{time}`, and `{name}`.
- Added log management controls in Terminal Settings.
- Unified remote serial access and automation access through one Serial Access service.
- Added CLI and MCP adapters for external automation.
- Added global highlight rules and per-tab watch tools for terminal output.

### Improvements

- Renamed the application to TermLink.
- Reworked the main UI around connection tabs, a connection panel, optional runtime logs, and optional command sets.
- Improved local serial add/scan workflows with baudrate, data bits, parity, stop bits, and flow control settings.
- Added multi-server remote serial client support.
- Added remote access controls for max clients, default permissions, and IP bans.
- Improved terminal find, selection, ANSI color rendering, and tab close styling.
- Improved startup time by lazy-loading optional network/dialog dependencies.
- Split tracked default configuration into `config.example.json`; local `config.json` is now runtime state and ignored by git.

### Fixes

- Fixed startup errors caused by saving dynamic remote serial sessions as local ports.
- Fixed remote serial state cleanup after disconnect and reconnect.
- Fixed remote access error reporting for password failures, banned clients, and unavailable servers.
- Fixed watch count drift by counting only new output since watch start.
- Fixed terminal scrollback tracking by recording true scroll events instead of estimating from screen diffs.

## v1.0.4 (2026-01-09)

### New

- Added Python 3.13+ Telnet support by replacing removed `telnetlib` usage with `SimpleTelnet`.

### Improvements

- Redesigned the About dialog with HTML formatting.
- Improved remote serial configuration persistence.
- Synced known device information to newly connected remote clients.

### Fixes

- Fixed remote serial configuration being incorrectly saved into `config.json`.
- Fixed timing issues that could prevent new clients from receiving device information.

## v1.0.3 (2026-01-08)

### New

- Added terminal find.
- Added terminal context menu actions for copy, paste, select all, find, break, clear, log actions, and scroll-to-bottom.
- Added SysRq-style break handling.
- Improved mouse text selection and double-click word selection.

### Improvements

- Improved terminal dirty-region rendering.
- Improved scrollbar styling.
- Unified code formatting in several UI modules.

### Fixes

- Fixed terminal line text extraction issues.
- Fixed find highlight cell matching.
- Fixed selection state updates during mouse handling.

## v1.0.2 and Earlier

See git history for earlier development changes.
