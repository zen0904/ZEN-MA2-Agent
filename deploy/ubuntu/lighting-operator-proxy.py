from __future__ import annotations

import argparse
import asyncio
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import subprocess
import time

DEFAULT_PEER = "desktop-aa2gr39"
DEFAULT_PEER_PORT = 18878
CACHE_TTL = 30.0
TAILSCALE = "tailscale"
_cache = {"peer": None, "ip": None, "expires": 0.0}


def resolve_peer(peer_name: str) -> str:
    now = time.monotonic()
    if _cache["peer"] == peer_name and _cache["ip"] and now < _cache["expires"]:
        return str(_cache["ip"])
    proc = subprocess.run(
        [TAILSCALE, "status", "--json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=5,
        check=False,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"tailscale status failed rc={proc.returncode}")
    data = json.loads(proc.stdout)
    matches: list[tuple[bool, str]] = []
    for item in (data.get("Peer") or {}).values():
        host = str(item.get("HostName") or "")
        dns = str(item.get("DNSName") or "").rstrip(".")
        short_dns = dns.split(".", 1)[0] if dns else ""
        if peer_name.lower() not in {host.lower(), short_dns.lower()}:
            continue
        ips = [ip for ip in (item.get("TailscaleIPs") or []) if ":" not in ip]
        if ips:
            matches.append((bool(item.get("Online")), ips[0]))
    if not matches:
        raise RuntimeError(f"Tailscale peer {peer_name!r} not found")
    matches.sort(reverse=True)
    ip = matches[0][1]
    _cache.update(peer=peer_name, ip=ip, expires=now + CACHE_TTL)
    return ip


async def pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while True:
            data = await reader.read(65536)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except (ConnectionError, asyncio.CancelledError):
        pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def handle_client(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    peer_name: str,
    peer_port: int,
) -> None:
    remote = writer.get_extra_info("peername")
    try:
        peer_ip = resolve_peer(peer_name)
        upstream_reader, upstream_writer = await asyncio.wait_for(
            asyncio.open_connection(peer_ip, peer_port),
            timeout=5,
        )
        logger.info("connected client=%s peer=%s:%s", remote, peer_ip, peer_port)
        await asyncio.gather(
            pipe(reader, upstream_writer),
            pipe(upstream_reader, writer),
        )
    except Exception as exc:
        logger.warning("proxy failure client=%s class=%s", remote, type(exc).__name__)
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def run_server(host: str, port: int, peer: str, peer_port: int) -> None:
    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, peer, peer_port),
        host,
        port,
    )
    logger.info("listening=%s:%s peer=%s:%s", host, port, peer, peer_port)
    async with server:
        await server.serve_forever()


def main() -> int:
    parser = argparse.ArgumentParser(description="ZEN Mini loopback proxy to Windows lighting operator facade")
    parser.add_argument("--listen-host", default="127.0.0.1")
    parser.add_argument("--listen-port", type=int, default=18878)
    parser.add_argument("--peer", default=DEFAULT_PEER)
    parser.add_argument("--peer-port", type=int, default=DEFAULT_PEER_PORT)
    parser.add_argument("--resolve-only", action="store_true")
    args = parser.parse_args()

    if args.resolve_only:
        print(json.dumps({"peer": args.peer, "ip": resolve_peer(args.peer)}, sort_keys=True))
        return 0

    global logger
    log_dir = Path("/var/log/zen-agent")
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("lighting-operator-proxy")
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(
        log_dir / "lighting-operator-proxy.log",
        maxBytes=1_000_000,
        backupCount=2,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)

    asyncio.run(run_server(args.listen_host, args.listen_port, args.peer, args.peer_port))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
