import argparse
import asyncio
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import subprocess
import time

TAILSCALE = Path(r"C:\Program Files\Tailscale\tailscale.exe")
DEFAULT_PEER = "zen-agent-server"
DEFAULT_PEER_PORT = 18876
CACHE_TTL = 30.0

_log_dir = Path.home() / "AppData" / "Local" / "ZEN-MA2-Agent" / "logs"
_log_dir.mkdir(parents=True, exist_ok=True)
log = logging.getLogger("zen-mini-proxy")
log.setLevel(logging.INFO)
_handler = RotatingFileHandler(_log_dir / "mini-controller-proxy.log", maxBytes=1_000_000, backupCount=2, encoding="utf-8")
_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
log.addHandler(_handler)

_cache = {"peer": None, "ip": None, "expires": 0.0}


def _tailscale_status():
    p = subprocess.run(
        [str(TAILSCALE), "status", "--json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=5,
        check=False,
        encoding="utf-8",
        errors="replace",
    )
    if p.returncode != 0:
        raise RuntimeError(f"tailscale status failed rc={p.returncode}")
    return json.loads(p.stdout)


def resolve_peer(peer_name: str) -> str:
    now = time.monotonic()
    if _cache["peer"] == peer_name and _cache["ip"] and now < _cache["expires"]:
        return _cache["ip"]
    data = _tailscale_status()
    peers = data.get("Peer") or {}
    matches = []
    for item in peers.values():
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


async def _pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
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


async def handle_client(reader, writer, peer_name: str, peer_port: int):
    remote = writer.get_extra_info("peername")
    try:
        peer_ip = resolve_peer(peer_name)
        upstream_reader, upstream_writer = await asyncio.wait_for(
            asyncio.open_connection(peer_ip, peer_port), timeout=5
        )
        log.info("connected client=%s peer=%s:%s", remote, peer_ip, peer_port)
        await asyncio.gather(
            _pipe(reader, upstream_writer),
            _pipe(upstream_reader, writer),
        )
    except Exception as exc:
        log.warning("proxy failure client=%s error=%s", remote, type(exc).__name__)
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def run_server(listen_host: str, listen_port: int, peer_name: str, peer_port: int):
    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, peer_name, peer_port),
        listen_host,
        listen_port,
    )
    sockets = ", ".join(str(s.getsockname()) for s in server.sockets or [])
    log.info("listening %s -> %s:%s", sockets, peer_name, peer_port)
    async with server:
        await server.serve_forever()


def main():
    ap = argparse.ArgumentParser(description="ZEN Windows localhost proxy to Mini over Tailscale")
    ap.add_argument("--listen-host", default="127.0.0.1")
    ap.add_argument("--listen-port", type=int, default=8876)
    ap.add_argument("--peer", default=DEFAULT_PEER)
    ap.add_argument("--peer-port", type=int, default=DEFAULT_PEER_PORT)
    ap.add_argument("--resolve-only", action="store_true")
    args = ap.parse_args()
    if args.resolve_only:
        print(json.dumps({"peer": args.peer, "ip": resolve_peer(args.peer)}, sort_keys=True))
        return 0
    asyncio.run(run_server(args.listen_host, args.listen_port, args.peer, args.peer_port))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
