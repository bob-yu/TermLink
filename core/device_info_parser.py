import re


IP_PATTERNS = (
    r"inet addr[:\s]*(\d+\.\d+\.\d+\.\d+)",
    r"inet\s+(\d+\.\d+\.\d+\.\d+)",
)


def parse_ip_from_ifconfig(text: str) -> str:
    """Return the first non-loopback IPv4 address found in ifconfig output."""
    for pattern in IP_PATTERNS:
        match = re.search(pattern, text)
        if not match:
            continue

        ip = match.group(1)
        if ip and not ip.startswith("127."):
            return ip

    return ""


def parse_version_from_command_output(text: str) -> str:
    match = re.search(
        r"cat\s+/system/bin/version\s*(.+?)\[root@",
        text,
        re.DOTALL,
    )
    if not match:
        return ""

    return re.sub(r"\s+", " ", match.group(1).strip()).strip()
