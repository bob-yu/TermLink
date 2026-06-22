from dataclasses import dataclass


@dataclass(frozen=True)
class NetworkAddress:
    host: str
    port: int


def parse_server_address(address: str, default_port: int) -> NetworkAddress:
    """Parse host[:port] using default_port when no port is present."""
    if ":" in address:
        host, port_text = address.rsplit(":", 1)
        if host == "0.0.0.0":
            host = "127.0.0.1"
        return NetworkAddress(host=host, port=int(port_text))
    if address == "0.0.0.0":
        address = "127.0.0.1"
    return NetworkAddress(host=address, port=default_port)
