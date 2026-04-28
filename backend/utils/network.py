"""Network security utilities — SSRF protection."""

import ipaddress
import socket
from urllib.parse import urlparse


# Private/reserved IP ranges that should not be accessed via SSRF
_PRIVATE_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def is_private_ip(url: str) -> bool:
    """Check if a URL resolves to a private/reserved IP address.

    Returns True if the URL's hostname resolves to a private IP (unsafe to fetch).
    Returns False if the URL is safe to fetch.
    """
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return True  # No hostname = unsafe

        # Resolve hostname to IP
        addrinfo = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for family, _, _, _, sockaddr in addrinfo:
            ip_str = sockaddr[0]
            ip = ipaddress.ip_address(ip_str)
            for network in _PRIVATE_NETWORKS:
                if ip in network:
                    return True
    except (socket.gaierror, ValueError, OSError):
        # If we can't resolve, treat as unsafe
        return True

    return False
