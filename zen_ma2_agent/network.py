from __future__ import annotations

import socket


def lan_ipv4_addresses() -> list[str]:
    addresses: set[str] = set()
    try:
        for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            address = item[4][0]
            if not address.startswith("127."):
                addresses.add(address)
    except OSError:
        pass
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("8.8.8.8", 80))
        address = probe.getsockname()[0]
        probe.close()
        if not address.startswith("127."):
            addresses.add(address)
    except OSError:
        pass
    return sorted(addresses)


def internet_online() -> bool:
    try:
        probe = socket.create_connection(("1.1.1.1", 53), timeout=0.35)
        probe.close()
        return True
    except OSError:
        return False
