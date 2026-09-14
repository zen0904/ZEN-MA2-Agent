"""Portable, replaceable LLM provider routing.

This module deliberately has no MA2 transport dependency.  Providers return
text only; the autonomous designer validates a typed document before anything
can reach a resolver or Builder.
"""

from __future__ import annotations

import json
import os
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..portable import portable_state_path


class ProviderUnavailable(RuntimeError):
    """A safe, key-free explanation that a slot could not serve a request."""


@dataclass(frozen=True)
class ProviderSlot:
    number: int
    provider_type: str
    model: str
    base_url: str
    api_key: str
    roles: tuple[str, ...]
    timeout_seconds: float

    #: Provider types that are expected to run without any credential (a
    #: local OpenAI-compatible server such as Ollama or llama.cpp).  Cloud
    #: types still require a non-empty ``api_key`` so a missing credential
    #: fails loudly instead of silently marking the slot unconfigured.
    LOCAL_TYPES = frozenset({"OPENAI_COMPATIBLE_LOCAL"})

    @property
    def configured(self) -> bool:
        if not (self.provider_type and self.model and self.base_url):
            return False
        if self.provider_type in self.LOCAL_TYPES:
            return True
        return bool(self.api_key)

    def supports(self, role: str) -> bool:
        return not self.roles or role.upper() in self.roles

    def safe_identity(self) -> dict[str, object]:
        return {
            "slot": self.number,
            "type": self.provider_type,
            "model": self.model,
            "base_url_configured": bool(self.base_url),
            "api_key_configured": bool(self.api_key),
            "api_key_required": self.provider_type not in self.LOCAL_TYPES,
            "roles": list(self.roles),
        }


def _read_private_env(path: Path | None = None) -> dict[str, str]:
    """Read a simple USB-local dotenv without printing its values."""
    path = path or portable_state_path("secrets") / "providers.private.env"
    values = {key: value for key, value in os.environ.items() if key.startswith("ZEN_PROVIDER_")}
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


def load_provider_slots(path: Path | None = None) -> tuple[str, tuple[ProviderSlot, ...]]:
    values = _read_private_env(path)
    mode = values.get("ZEN_PROVIDER_MODE", "PRIMARY_ONLY").strip().upper() or "PRIMARY_ONLY"
    if mode not in {"PRIMARY_ONLY", "FALLBACK", "ROUTED"}:
        raise ValueError("ZEN_PROVIDER_MODE must be PRIMARY_ONLY, FALLBACK, or ROUTED.")
    slots: list[ProviderSlot] = []
    for number in range(1, 4):
        prefix = f"ZEN_PROVIDER_{number}_"
        roles = tuple(role.strip().upper() for role in values.get(prefix + "ROLES", "").split(",") if role.strip())
        try:
            timeout = float(values.get(prefix + "TIMEOUT_SECONDS", "45"))
        except ValueError as exc:
            raise ValueError(f"Provider {number} timeout must be numeric.") from exc
        # Portable CPU inference can legitimately take several minutes for a
        # long structured prompt.  Keep a finite upper bound, while allowing a
        # user-configured local provider enough time to complete without a
        # false transport failure.
        if not 1 <= timeout <= 900:
            raise ValueError(f"Provider {number} timeout must be from 1 to 900 seconds.")
        slots.append(ProviderSlot(
            number=number,
            provider_type=values.get(prefix + "TYPE", "").strip().upper(),
            model=values.get(prefix + "MODEL", "").strip(),
            base_url=values.get(prefix + "BASE_URL", "").strip(),
            api_key=values.get(prefix + "API_KEY", "").strip(),
            roles=roles,
            timeout_seconds=timeout,
        ))
    return mode, tuple(slots)


def _safe_http_error_summary(exc: HTTPError) -> str:
    """Return a bounded, non-secret diagnostic extracted from an HTTP error."""
    try:
        raw = exc.read(4096).decode("utf-8", errors="replace")
    except Exception:
        return ""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return ""
    if not isinstance(payload, dict):
        return ""
    error = payload.get("error")
    if isinstance(error, dict):
        value = error.get("message") or error.get("detail")
    else:
        value = payload.get("message") or payload.get("detail")
    if not isinstance(value, str):
        return ""
    text = value.strip()
    lowered = text.casefold()
    if any(token in lowered for token in ("authorization", "api_key", "apikey", "bearer", "token", "secret")):
        return ""
    return " ".join(text.split())[:500]


class OpenAICompatibleHTTPAdapter:
    """Small adapter for OpenAI-compatible Chat Completions endpoints.

    Native providers can be added later behind the same ``complete`` method;
    no artistic logic belongs in an adapter.
    """

    def complete(self, slot: ProviderSlot, *, system: str, user: str) -> str:
        if slot.provider_type not in {"OPENAI_COMPATIBLE", "OPENAI", "OPENAI_COMPATIBLE_LOCAL"}:
            raise ProviderUnavailable(f"Provider slot {slot.number} type is not implemented: {slot.provider_type or 'UNSET'}")
        endpoint = slot.base_url.rstrip("/")
        if not endpoint.endswith("/chat/completions"):
            endpoint += "/chat/completions"
        body = json.dumps({
            "model": slot.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        # A local, key-free server should not receive a bogus Bearer header;
        # only attach Authorization when a credential is actually configured.
        if slot.api_key:
            headers["Authorization"] = f"Bearer {slot.api_key}"
        request = Request(endpoint, data=body, method="POST", headers=headers)
        try:
            with urlopen(request, timeout=slot.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = _safe_http_error_summary(exc)
            suffix = f": {detail}" if detail else ""
            raise ProviderUnavailable(f"Provider slot {slot.number} request failed: HTTPError {exc.code}{suffix}") from exc
        except (URLError, TimeoutError, socket.timeout, json.JSONDecodeError) as exc:
            # Do not leak endpoint query details, response bodies, or credentials.
            raise ProviderUnavailable(f"Provider slot {slot.number} request failed: {type(exc).__name__}") from exc
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderUnavailable(f"Provider slot {slot.number} returned no chat completion content.") from exc
        if not isinstance(content, str) or not content.strip():
            raise ProviderUnavailable(f"Provider slot {slot.number} returned empty chat completion content.")
        return content


class ProviderRouter:
    def __init__(self, mode: str, slots: Iterable[ProviderSlot], adapter: OpenAICompatibleHTTPAdapter | None = None):
        self.mode = mode
        self.slots = tuple(slots)
        self.adapter = adapter or OpenAICompatibleHTTPAdapter()

    @classmethod
    def from_portable_config(cls, path: Path | None = None) -> "ProviderRouter":
        mode, slots = load_provider_slots(path)
        return cls(mode, slots)

    def configured_slots(self) -> tuple[ProviderSlot, ...]:
        return tuple(slot for slot in self.slots if slot.configured)

    def _candidates(self, role: str) -> tuple[ProviderSlot, ...]:
        configured = tuple(slot for slot in self.slots if slot.configured and slot.supports(role))
        if self.mode == "PRIMARY_ONLY":
            return configured[:1]
        if self.mode == "FALLBACK":
            return configured
        # ROUTED: pick eligible role-specific slots first while retaining
        # configured general-purpose slots in deterministic slot order.
        specific = tuple(slot for slot in configured if slot.roles)
        general = tuple(slot for slot in configured if not slot.roles)
        return specific + general

    def complete(self, *, role: str, system: str, user: str) -> tuple[str, ProviderSlot]:
        candidates = self._candidates(role)
        if not candidates:
            raise ProviderUnavailable(f"No configured provider slot is eligible for role {role.upper()}.")
        failures: list[str] = []
        for slot in candidates:
            try:
                return self.adapter.complete(slot, system=system, user=user), slot
            except ProviderUnavailable as exc:
                failures.append(f"slot {slot.number}: {exc}")
                if self.mode == "PRIMARY_ONLY":
                    break
        raise ProviderUnavailable("; ".join(failures) or "No eligible provider completed the request.")
