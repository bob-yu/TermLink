import argparse
import json
import sys
import threading

from .serial_access_client import SerialAccessApiClient


def _print_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _client_from_args(args):
    return SerialAccessApiClient(
        host=args.host,
        port=args.server_port,
        password=args.password,
        timeout=args.timeout,
        source="cli",
    )


def main(argv=None):
    parser = argparse.ArgumentParser(prog="serialtool", description="TermLink automation CLI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", dest="server_port", type=int, default=56337)
    parser.add_argument("--password", default="")
    parser.add_argument("--timeout", type=float, default=10.0)

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    sub.add_parser("list-ports")

    state = sub.add_parser("state")
    state.add_argument("serial_port")
    state = sub.add_parser("get-port-state")
    state.add_argument("serial_port")

    find = sub.add_parser("find-ip")
    find.add_argument("device_ip")
    find = sub.add_parser("find-port-by-ip")
    find.add_argument("device_ip")

    write = sub.add_parser("write")
    write.add_argument("serial_port")
    write.add_argument("data")
    write = sub.add_parser("write-data")
    write.add_argument("serial_port")
    write.add_argument("data")

    watch = sub.add_parser("watch")
    watch.add_argument("serial_port")
    watch.add_argument("--duration", type=float, default=2.0)
    watch.add_argument("--expect", default=None)
    watch.add_argument("--idle-timeout", type=float, default=None)
    watch.add_argument("--start-seq", type=int, default=None)
    watch.add_argument("--from", dest="from_position", choices=("latest", "oldest", "seq"), default="latest")
    watch.add_argument("--regex", action="store_true")

    buffer_state = sub.add_parser("buffer-state")
    buffer_state.add_argument("serial_port")
    buffer_state = sub.add_parser("buffer")
    buffer_state.add_argument("serial_port")

    cmd = sub.add_parser("command")
    cmd.add_argument("serial_port")
    cmd.add_argument("serial_command")
    cmd.add_argument("--expect", default=None)
    cmd.add_argument("--duration", type=float, default=5.0)
    cmd.add_argument("--idle-timeout", type=float, default=0.3)
    cmd.add_argument("--regex", action="store_true")
    cmd = sub.add_parser("send-command")
    cmd.add_argument("serial_port")
    cmd.add_argument("serial_command")
    cmd.add_argument("--expect", default=None)
    cmd.add_argument("--command-timeout", type=int, default=30)
    cmd.add_argument("--idle-timeout", type=float, default=None)
    cmd.add_argument("--regex", action="store_true")

    brk = sub.add_parser("break")
    brk.add_argument("serial_port")
    brk = sub.add_parser("send-break")
    brk.add_argument("serial_port")

    log = sub.add_parser("log")
    log.add_argument("serial_port")
    log.add_argument("--lines", type=int, default=100)
    log = sub.add_parser("get-log-snapshot")
    log.add_argument("serial_port")
    log.add_argument("--lines", type=int, default=100)

    update_ip = sub.add_parser("update-device-ip")
    update_ip.add_argument("serial_port")
    update_ip.add_argument("device_ip")

    fetch_ip = sub.add_parser("fetch-device-ip")
    fetch_ip.add_argument("serial_port")
    fetch_ip.add_argument("--fetch-timeout", type=int, default=10)

    request = sub.add_parser("request")
    request.add_argument("action")
    request.add_argument("--params", default="{}")

    send_watch = sub.add_parser("send-and-watch")
    send_watch.add_argument("serial_port")
    send_watch.add_argument("data")
    send_watch.add_argument("--watch-seconds", type=float, default=2.0)

    console = sub.add_parser("console")
    console.add_argument("serial_port")

    args = parser.parse_args(argv)

    try:
        with _client_from_args(args) as client:
            if args.command in ("list", "list-ports"):
                response = client.request("list")
            elif args.command in ("state", "get-port-state"):
                response = client.request("state", {"port": args.serial_port})
            elif args.command in ("find-ip", "find-port-by-ip"):
                response = client.request("find_ip", {"device_ip": args.device_ip})
            elif args.command in ("write", "write-data"):
                response = client.request("write", {"port": args.serial_port, "data": args.data})
            elif args.command == "watch":
                response = client.watch(
                    args.serial_port,
                    duration=args.duration,
                    expect=args.expect,
                    idle_timeout=args.idle_timeout,
                    start_seq=args.start_seq,
                    from_position=args.from_position,
                    regex=args.regex,
                )
            elif args.command in ("buffer-state", "buffer"):
                response = client.buffer_state(args.serial_port)
            elif args.command == "command":
                response = client.request("command", {
                    "port": args.serial_port,
                    "command": args.serial_command,
                    "expect": args.expect,
                    "duration": args.duration,
                    "idle_timeout": args.idle_timeout,
                    "regex": args.regex,
                })
            elif args.command == "send-command":
                response = client.request("command", {
                    "port": args.serial_port,
                    "command": args.serial_command,
                    "expect": args.expect,
                    "timeout": args.command_timeout,
                    "idle_timeout": args.idle_timeout,
                    "regex": args.regex,
                })
            elif args.command in ("break", "send-break"):
                response = client.request("break", {"port": args.serial_port})
            elif args.command in ("log", "get-log-snapshot"):
                response = client.request("log", {"port": args.serial_port, "lines": args.lines})
            elif args.command == "update-device-ip":
                response = client.request("update_device_ip", {
                    "port": args.serial_port,
                    "device_ip": args.device_ip,
                })
            elif args.command == "fetch-device-ip":
                response = client.request("fetch_device_ip", {
                    "port": args.serial_port,
                    "timeout": args.fetch_timeout,
                })
            elif args.command == "request":
                response = client.request(args.action, json.loads(args.params))
            elif args.command == "send-and-watch":
                response = client.send_and_watch(args.serial_port, args.data, args.watch_seconds)
            elif args.command == "console":
                response = client.subscribe(args.serial_port)
                _print_json(response)
                stop = threading.Event()

                def reader():
                    while not stop.is_set():
                        event = client.recv_event()
                        if event is None:
                            stop.set()
                            break
                        data = event.get("data", {})
                        content = data.get("content")
                        if content is not None:
                            print(content, end="", flush=True)

                thread = threading.Thread(target=reader, daemon=True)
                thread.start()
                try:
                    for line in sys.stdin:
                        client.request("write", {"port": args.serial_port, "data": line})
                except KeyboardInterrupt:
                    pass
                finally:
                    stop.set()
                return 0
            else:
                parser.error(f"Unknown command: {args.command}")
                return 2
    except ConnectionError as exc:
        response = {"code": 5, "message": str(exc)}

    _print_json(response)
    return 0 if response.get("code", 1) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

