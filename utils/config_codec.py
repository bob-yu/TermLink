from typing import Any, Dict

from .config_schema import (
    DEFAULT_REMOTE_SERIAL_PORT,
    AppConfigData,
    CommandSetData,
    HighlightRuleData,
    LoginConfigData,
    PortConfigData,
)


def create_default_config() -> AppConfigData:
    return AppConfigData(
        serial_ports=[],
        log_dir="logs",
        auto_reconnect=True,
        reconnect_interval=5,
        scan_patterns=["/dev/ttyUSB*", "/dev/ttyACM*"],
        serial_access_mode="disabled",
        serial_access_host="0.0.0.0",
        serial_access_port=DEFAULT_REMOTE_SERIAL_PORT,
        serial_access_server_address="",
        scrollback_lines=5000,
        terminal_font_family="",
        terminal_font_size=11,
        log_enabled=True,
        log_timestamp=True,
        window_geometry="",
        window_state="",
        show_connections_panel=True,
        show_runtime_log_panel=False,
        show_command_sets_panel=False,
        command_sets_panel_width=140,
        command_sets=[],
        highlight_rules=[],
        serial_access_default_permission="read-write",
        serial_access_banned_ips=[],
    )


def parse_config(data: Dict[str, Any]) -> AppConfigData:
    ports = []
    for port_data in data.get("serial_ports", []):
        login_data = port_data.get("login", {})
        login_config = LoginConfigData(
            username=login_data.get("username", "root"),
            password=login_data.get("password", "root"),
            login_prompt=login_data.get("login_prompt", "login:"),
            password_prompt=login_data.get("password_prompt", "Password:"),
            shell_prompt=login_data.get("shell_prompt", ["#", "$"]),
        )

        ports.append(
            PortConfigData(
                name=port_data.get("name", ""),
                port=port_data.get("port", ""),
                baudrate=port_data.get("baudrate", 115200),
                data_bits=port_data.get("data_bits", port_data.get("bytesize", 8)),
                parity=port_data.get("parity", "N"),
                stop_bits=port_data.get("stop_bits", port_data.get("stopbits", 1.0)),
                flow_control=port_data.get("flow_control", "none"),
                login=login_config,
                auto_commands=port_data.get("auto_commands", []),
                keywords=port_data.get("keywords", {}),
            )
        )

    serial_access_port = data.get(
        "serial_access_port",
        data.get("network_port", DEFAULT_REMOTE_SERIAL_PORT),
    )

    command_sets = []
    for item in data.get("command_sets", []):
        name = str(item.get("name", "")).strip()
        commands = [
            str(command).strip()
            for command in item.get("commands", [])
            if str(command).strip()
        ]
        if name and commands:
            command_sets.append(CommandSetData(name=name, commands=commands))

    highlight_rules = []
    for item in data.get("highlight_rules", []):
        pattern = str(item.get("pattern", "")).strip()
        if not pattern:
            continue
        highlight_rules.append(
            HighlightRuleData(
                name=str(item.get("name", "")).strip(),
                pattern=pattern,
                color=str(item.get("color", "#fff3cd")).strip() or "#fff3cd",
                case_sensitive=bool(item.get("case_sensitive", False)),
                regex=bool(item.get("regex", False)),
                enabled=bool(item.get("enabled", True)),
            )
        )

    return AppConfigData(
        serial_ports=ports,
        log_dir=data.get("log_dir", "logs"),
        auto_reconnect=data.get("auto_reconnect", True),
        reconnect_interval=data.get("reconnect_interval", 5),
        scan_patterns=data.get("scan_patterns", ["/dev/ttyUSB*", "/dev/ttyACM*"]),
        serial_access_mode=data.get("serial_access_mode", data.get("network_mode", "disabled")),
        serial_access_host=data.get("serial_access_host", data.get("network_host", "0.0.0.0")),
        serial_access_port=serial_access_port,
        serial_access_server_address=data.get(
            "serial_access_server_address",
            data.get("server_address", ""),
        ),
        scrollback_lines=data.get("scrollback_lines", 5000),
        terminal_font_family=data.get("terminal_font_family", ""),
        terminal_font_size=data.get("terminal_font_size", 11),
        log_enabled=data.get("log_enabled", True),
        log_timestamp=data.get("log_timestamp", True),
        log_name_pattern=data.get("log_name_pattern", "{port}_{date}_{time}"),
        log_max_days=data.get("log_max_days", 30),
        log_max_total_size_mb=data.get("log_max_total_size_mb", 500),
        log_max_file_size_mb=data.get("log_max_file_size_mb", 50),
        log_auto_clean=data.get("log_auto_clean", True),
        serial_access_enabled=data.get("serial_access_enabled", True),
        serial_access_password=data.get("serial_access_password", ""),
        serial_access_client_password=data.get(
            "serial_access_client_password",
            data.get("serial_access_password", ""),
        ),
        serial_access_max_clients=data.get("serial_access_max_clients", 16),
        serial_access_default_permission=data.get("serial_access_default_permission", "read-write"),
        serial_access_banned_ips=list(data.get("serial_access_banned_ips", [])),
        window_geometry=data.get("window_geometry", ""),
        window_state=data.get("window_state", ""),
        show_connections_panel=data.get("show_connections_panel", True),
        show_runtime_log_panel=data.get("show_runtime_log_panel", False),
        show_command_sets_panel=data.get("show_command_sets_panel", False),
        command_sets_panel_width=data.get("command_sets_panel_width", 140),
        command_sets=command_sets,
        highlight_rules=highlight_rules,
    )


def serialize_config(config: AppConfigData) -> Dict[str, Any]:
    ports = []
    for port in config.serial_ports:
        ports.append(
            {
                "name": port.name,
                "port": port.port,
                "baudrate": port.baudrate,
                "data_bits": port.data_bits,
                "parity": port.parity,
                "stop_bits": port.stop_bits,
                "flow_control": port.flow_control,
                "login": {
                    "username": port.login.username,
                    "password": port.login.password,
                    "login_prompt": port.login.login_prompt,
                    "password_prompt": port.login.password_prompt,
                    "shell_prompt": port.login.shell_prompt,
                },
                "auto_commands": port.auto_commands,
                "keywords": port.keywords,
            }
        )

    return {
        "scan_patterns": config.scan_patterns,
        "serial_ports": ports,
        "log_dir": config.log_dir,
        "auto_reconnect": config.auto_reconnect,
        "reconnect_interval": config.reconnect_interval,
        "serial_access_mode": config.serial_access_mode,
        "serial_access_host": config.serial_access_host,
        "serial_access_port": config.serial_access_port,
        "serial_access_server_address": config.serial_access_server_address,
        "scrollback_lines": config.scrollback_lines,
        "terminal_font_family": config.terminal_font_family,
        "terminal_font_size": config.terminal_font_size,
        "log_enabled": config.log_enabled,
        "log_timestamp": config.log_timestamp,
        "log_name_pattern": config.log_name_pattern,
        "log_max_days": config.log_max_days,
        "log_max_total_size_mb": config.log_max_total_size_mb,
        "log_max_file_size_mb": config.log_max_file_size_mb,
        "log_auto_clean": config.log_auto_clean,
        "serial_access_enabled": config.serial_access_enabled,
        "serial_access_password": config.serial_access_password,
        "serial_access_client_password": config.serial_access_client_password,
        "serial_access_max_clients": config.serial_access_max_clients,
        "serial_access_default_permission": config.serial_access_default_permission,
        "serial_access_banned_ips": config.serial_access_banned_ips,
        "window_geometry": config.window_geometry,
        "window_state": config.window_state,
        "show_connections_panel": config.show_connections_panel,
        "show_runtime_log_panel": config.show_runtime_log_panel,
        "show_command_sets_panel": config.show_command_sets_panel,
        "command_sets_panel_width": config.command_sets_panel_width,
        "command_sets": [
            {
                "name": command_set.name,
                "commands": command_set.commands,
            }
            for command_set in config.command_sets
        ],
        "highlight_rules": [
            {
                "name": rule.name,
                "pattern": rule.pattern,
                "color": rule.color,
                "case_sensitive": rule.case_sensitive,
                "regex": rule.regex,
                "enabled": rule.enabled,
            }
            for rule in config.highlight_rules
        ],
    }
