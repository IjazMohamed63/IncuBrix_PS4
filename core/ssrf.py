import ipaddress
import socket
from urllib.parse import urlparse
from typing import List, Optional
from core.errors import ErrorCode, IncuBrixError
from core.logging import get_logger

logger = get_logger("ssrf_validator")

# Prohibited CIDR blocks for SSRF protection
BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),          # Current network
    ipaddress.ip_network("10.0.0.0/8"),         # Private RFC1918
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback
    ipaddress.ip_network("169.254.0.0/16"),     # Link-local / Cloud metadata (169.254.169.254)
    ipaddress.ip_network("172.16.0.0/12"),      # Private RFC1918
    ipaddress.ip_network("192.168.0.0/16"),     # Private RFC1918
    ipaddress.ip_network("224.0.0.0/4"),        # Multicast
    ipaddress.ip_network("240.0.0.0/4"),        # Reserved
    ipaddress.ip_network("255.255.255.255/32"), # Broadcast
    ipaddress.ip_network("::1/128"),            # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),           # IPv6 Unique local
    ipaddress.ip_network("fe80::/10"),          # IPv6 Link-local
]


def is_ip_allowed(ip_str: str, allow_local_for_tests: bool = False) -> bool:
    """Verifies that an IP address is not private, loopback, or cloud metadata."""
    if allow_local_for_tests:
        return True
    try:
        ip = ipaddress.ip_address(ip_str)
        for net in BLOCKED_IP_NETWORKS:
            if ip in net:
                return False
        return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved)
    except ValueError:
        return False


def validate_url_ssrf_safe(url: str, allow_local_for_tests: bool = False) -> str:
    """Performs SSRF validation on target URL.
    
    Checks scheme, parses host, resolves DNS, and blocks private/metadata IPs.
    Raises IncuBrixError if URL is unsafe.
    """
    if not url:
        raise IncuBrixError(
            code=ErrorCode.VALIDATION_ERROR,
            message="URL cannot be empty.",
            status_code=400,
        )

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise IncuBrixError(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"SSRF violation: Prohibited URL scheme '{parsed.scheme}'. Only http and https allowed.",
            status_code=400,
        )

    hostname = parsed.hostname
    if not hostname:
        raise IncuBrixError(
            code=ErrorCode.VALIDATION_ERROR,
            message="SSRF violation: Missing hostname in URL.",
            status_code=400,
        )

    # Check for direct cloud metadata or localhost hostnames
    lowered_host = hostname.lower()
    if not allow_local_for_tests:
        if lowered_host in ("localhost", "127.0.0.1", "169.254.169.254", "metadata.google.internal", "instance-data"):
            raise IncuBrixError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"SSRF violation: Access to prohibited host '{hostname}' is denied.",
                status_code=403,
            )

    # DNS Resolution & IP checking
    try:
        resolved_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise IncuBrixError(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"SSRF violation: Failed to resolve hostname '{hostname}': {str(e)}",
            status_code=400,
        )

    for item in resolved_infos:
        ip_addr = item[4][0]
        if not is_ip_allowed(ip_addr, allow_local_for_tests=allow_local_for_tests):
            logger.warning(f"SSRF blocked connection to prohibited IP: {ip_addr} (host: {hostname})")
            raise IncuBrixError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"SSRF violation: Hostname '{hostname}' resolves to prohibited IP '{ip_addr}'.",
                status_code=403,
                details={"hostname": hostname, "resolved_ip": ip_addr},
            )

    return url
