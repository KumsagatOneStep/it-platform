import ipaddress
from collections.abc import Collection

from starlette.requests import Request


def _is_trusted(address: str, trusted_proxies: Collection[str]) -> bool:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    return any(ip in ipaddress.ip_network(network, strict=False) for network in trusted_proxies)


def client_ip(request: Request, trusted_proxies: Collection[str]) -> str:
    """IP клиента. X-Forwarded-For учитывается только от доверенного прокси."""
    peer = request.client.host if request.client else "unknown"
    if not _is_trusted(peer, trusted_proxies):
        return peer
    forwarded = request.headers.get("x-forwarded-for", "")
    hops = [hop.strip() for hop in forwarded.split(",") if hop.strip()]
    for hop in reversed(hops):
        if not _is_trusted(hop, trusted_proxies):
            return hop
    return peer
