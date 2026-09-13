"""Read-only connectivity diagnostic for the USB-local provider slot 1.

This intentionally does not import or alter the ProviderRouter.  It checks the
OpenAI-compatible ``GET /models`` discovery endpoint only, so it cannot create
chat completions or trigger any MA2 operation.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ProviderCheckResult:
    status: str
    base_url: str
    models: tuple[str, ...] = ()
    detail: str = ""


def read_private_env(path: Path) -> dict[str, str]:
    """Read the small dotenv subset needed by this standalone diagnostic."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key.startswith("ZEN_PROVIDER_"):
            values[key] = value.strip().strip('"').strip("'")
    return values


def models_url(base_url: str) -> str:
    return base_url.rstrip("/") + "/models"


def _model_names(payload: object) -> tuple[str, ...] | None:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        return None
    names: list[str] = []
    for entry in payload["data"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str) or not entry["id"].strip():
            return None
        names.append(entry["id"].strip())
    return tuple(names)


def check_slot_1(base_url: str, *, opener: Callable[..., object] = urlopen, timeout_seconds: float = 3.0) -> ProviderCheckResult:
    """Classify reachability separately from OpenAI-compatible response shape."""
    target = models_url(base_url)
    request = Request(target, method="GET", headers={"Accept": "application/json"})
    try:
        with opener(request, timeout=timeout_seconds) as response:
            raw = response.read()
    except (URLError, socket.timeout, TimeoutError, ConnectionRefusedError) as exc:
        return ProviderCheckResult("NOT_REACHABLE", base_url, detail=type(exc).__name__)
    except HTTPError as exc:
        # HTTP response means a listener answered, but the endpoint is not the
        # expected discovery contract. Do not misreport it as a network fault.
        return ProviderCheckResult("UNEXPECTED_RESPONSE", base_url, detail=f"HTTP {exc.code}")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return ProviderCheckResult("UNEXPECTED_RESPONSE", base_url, detail=type(exc).__name__)
    names = _model_names(payload)
    if names is None:
        return ProviderCheckResult("UNEXPECTED_RESPONSE", base_url, detail="missing OpenAI-compatible data[].id inventory")
    return ProviderCheckResult("OK", base_url, models=names)


def _zen_home(value: str | None) -> Path:
    raw = value or os.environ.get("ZEN_HOME", "")
    if not raw.strip():
        raise ValueError("ZEN_HOME is not set. Launch from the portable ZEN launcher or pass --zen-home.")
    return Path(raw).expanduser().resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only local OpenAI-compatible provider health check.")
    parser.add_argument("--zen-home", help="Portable ZEN_HOME; defaults to the ZEN_HOME environment variable.")
    parser.add_argument("--timeout", type=float, default=3.0, help="GET /models timeout in seconds (default: 3).")
    args = parser.parse_args()
    try:
        home = _zen_home(args.zen_home)
        if args.timeout <= 0:
            raise ValueError("--timeout must be positive.")
    except ValueError as exc:
        print(f"LOCAL PROVIDER CHECK: CONFIG ERROR - {exc}")
        return 2
    values = read_private_env(home / "secrets" / "providers.private.env")
    base_url = values.get("ZEN_PROVIDER_1_BASE_URL", "").strip()
    if not base_url:
        print("LOCAL PROVIDER CHECK: SLOT 1 BASE URL NOT CONFIGURED")
        return 2
    result = check_slot_1(base_url, timeout_seconds=args.timeout)
    print(f"LOCAL PROVIDER CHECK: slot 1 - {result.status}")
    print(f"Base URL: {result.base_url}")
    if result.status == "NOT_REACHABLE":
        print("server may not be started, or base_url is incorrect")
        return 1
    if result.status == "UNEXPECTED_RESPONSE":
        print("connected but this does not look like an OpenAI-compatible server; check base_url")
        print(f"Detail: {result.detail}")
        return 1
    print("Models:")
    for name in result.models:
        print(f"- {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
