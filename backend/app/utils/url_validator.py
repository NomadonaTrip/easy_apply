"""URL validation utility for preventing SSRF attacks."""

import ipaddress
import socket
from typing import Optional
from urllib.parse import urlparse

BLOCKED_HOSTNAMES = {"localhost", "0.0.0.0"}


def validate_url(url: str) -> tuple[bool, Optional[str]]:
    """
    Validate a URL is safe to fetch (not targeting internal/private resources).

    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is None.
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL format"

    if parsed.scheme not in ("http", "https"):
        return False, "URL must use http or https scheme"

    hostname = parsed.hostname
    if not hostname:
        return False, "URL must include a hostname"

    if hostname.lower() in BLOCKED_HOSTNAMES:
        return False, "URLs targeting localhost are not allowed"

    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False, f"Could not resolve hostname: {hostname}"

    for addr_info in addr_infos:
        ip_str = addr_info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue

        if ip.is_private or ip.is_reserved or ip.is_loopback or ip.is_link_local:
            return False, "URLs targeting private or internal networks are not allowed"

    return True, None
