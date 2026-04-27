from __future__ import annotations

import socket
import time

BOOT_TIME: float = time.time()


def uptime_seconds() -> float:
    return max(0.0, time.time() - BOOT_TIME)


def get_lan_ip() -> str:
    """Best-effort local LAN address. Uses the trick of opening a UDP socket
    to a routable address (no packets sent) and reading the chosen source IP."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(("8.8.8.8", 80))
            return str(sock.getsockname()[0])
        finally:
            sock.close()
    except OSError:
        return "127.0.0.1"


def format_uptime(seconds: float) -> str:
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"
