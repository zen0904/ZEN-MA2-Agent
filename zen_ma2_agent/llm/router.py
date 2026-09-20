"""Portable, replaceable LLM provider routing.

This module deliberately has no MA2 transport dependency.  Providers return
text only; the autonomous designer validates a typed document before anything
can reach a resolver or Builder.
"""

from __future__ import annotations

import json
import os
import socket
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    priority: int = 100
    cost_class: str = "UNKNOWN"
    response_format: str = "JSON_OBJECT"

    #: Provider types that are expected to run without any credential (a
    #: local OpenAI-compatible server such as Ollama or llama.cpp).  Cloud
    #: types still require a non-empty ``api_key`` so a missing credential
    #: fails loudly instead of silently marking the slot unconfigured.
    LOCAL_TYPES = frozenset({"OPENAI_COMPATIBLE_LOCAL"})
    COST_CLASSES = frozenset({"FREE", "LOCAL", "PAID", "UNKNOWN"})
    RESPONSE_FORMATS = frozenset({"JSON_OBJECT", "NONE"})

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
            "priority": self.priority,
            "cost_class": self.cost_class,
            "response_format": self.response_format,
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


def _provider_slot_count(values: dict[str, str]) -> int:
    """Return a bounded slot count while preserving the historical 3-slot default."""
    raw = values.get("ZEN_PROVIDER_SLOT_COUNT", "").strip()
    if raw:
        try:
            explicit = int(raw)
        except ValueError as exc:
            raise ValueError("ZEN_PROVIDER_SLOT_COUNT must be an integer.") from exc
        if not 1 <= explicit <= 16:
            raise ValueError("ZEN_PROVIDER_SLOT_COUNT must be from 1 to 16.")
    else:
        explicit = 3
    detected = [
        int(match.group(1))
        for key in values
        if (match := re.match(r"^ZEN_PROVIDER_(\d+)_", key))
    ]
    return max(explicit, max(detected, default=0), 3)


def load_provider_slots(path: Path | None = None) -> tuple[str, tuple[ProviderSlot, ...]]:
    values = _read_private_env(path)
    mode = values.get("ZEN_PROVIDER_MODE", "PRIMARY_ONLY").strip().upper() or "PRIMARY_ONLY"
    if mode not in {"PRIMARY_ONLY", "FALLBACK", "ROUTED", "FREE_FIRST"}:
        raise ValueError("ZEN_PROVIDER_MODE must be PRIMARY_ONLY, FALLBACK, ROUTED, or FREE_FIRST.")
    slots: list[ProviderSlot] = []
    for number in range(1, _provider_slot_count(values) + 1):
        prefix = f"ZEN_PROVIDER_{number}_"
        provider_type = values.get(prefix + "TYPE", "").strip().upper()
        roles = tuple(role.strip().upper() for role in values.get(prefix + "ROLES", "").split(",") if role.strip())
        try:
            timeout = float(values.get(prefix + "TIMEOUT_SECONDS", "45"))
        except ValueError as exc:
            raise ValueError(f"Provider {number} timeout must be numeric.") from exc
        if not 1 <= timeout <= 900:
            raise ValueError(f"Provider {number} timeout must be from 1 to 900 seconds.")
        try:
            priority = int(values.get(prefix + "PRIORITY", "100"))
        except ValueError as exc:
            raise ValueError(f"Provider {number} priority must be an integer.") from exc
        if not 0 <= priority <= 10000:
            raise ValueError(f"Provider {number} priority must be from 0 to 10000.")
        default_cost = "LOCAL" if provider_type in ProviderSlot.LOCAL_TYPES else "UNKNOWN"
        cost_class = values.get(prefix + "COST_CLASS", default_cost).strip().upper() or default_cost
        if cost_class not in ProviderSlot.COST_CLASSES:
            raise ValueError(
                f"Provider {number} cost class must be FREE, LOCAL, PAID, or UNKNOWN."
            )
        response_format = values.get(prefix + "RESPONSE_FORMAT", "JSON_OBJECT").strip().upper() or "JSON_OBJECT"
        if response_format not in ProviderSlot.RESPONSE_FORMATS:
            raise ValueError(
                f"Provider {number} response format must be JSON_OBJECT or NONE."
            )
        slots.append(ProviderSlot(
            number=number,
            provider_type=provider_type,
            model=values.get(prefix + "MODEL", "").strip(),
            base_url=values.get(prefix + "BASE_URL", "").strip(),
            api_key=values.get(prefix + "API_KEY", "").strip(),
            roles=roles,
            timeout_seconds=timeout,
            priority=priority,
            cost_class=cost_class,
            response_format=response_format,
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
        body_payload: dict[str, object] = {
            "model": slot.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0.2,
        }
        if slot.response_format == "JSON_OBJECT":
            body_payload["response_format"] = {"type": "json_object"}
        body = json.dumps(body_payload).encode("utf-8")
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

    def candidates(self, role: str) -> tuple[ProviderSlot, ...]:
        configured = tuple(slot for slot in self.slots if slot.configured and slot.supports(role))
        if self.mode == "PRIMARY_ONLY":
            return configured[:1]
        if self.mode == "FALLBACK":
            return configured
        if self.mode == "ROUTED":
            # Role-scoped providers win over general-purpose providers.
            # Priority only orders peers inside each class, preserving the
            # historical "specific before general" behavior.
            specific = tuple(sorted((slot for slot in configured if slot.roles), key=lambda slot: (slot.priority, slot.number)))
            general = tuple(sorted((slot for slot in configured if not slot.roles), key=lambda slot: (slot.priority, slot.number)))
            return specific + general
        # FREE_FIRST is explicit policy, not billing autodetection. Operators
        # label each slot's current billing class in private config. A 429,
        # outage, or provider error naturally falls through to the next slot.
        cost_rank = {"FREE": 0, "LOCAL": 1, "UNKNOWN": 2, "PAID": 3}
        return tuple(sorted(
            configured,
            key=lambda slot: (
                cost_rank.get(slot.cost_class, 2),
                0 if slot.roles else 1,
                slot.priority,
                slot.number,
            ),
        ))

    def complete(self, *, role: str, system: str, user: str) -> tuple[str, ProviderSlot]:
        candidates = self.candidates(role)
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

    def complete_parallel(
        self,
        *,
        role: str,
        system: str,
        user: str,
        limit: int = 2,
    ) -> tuple[tuple[str, ProviderSlot], ...]:
        """Fan one bounded role request out to independent eligible providers.

        Results are returned in deterministic router preference order rather
        than completion order. One provider failing does not cancel other
        providers. This method only distributes model inference; it does not
        merge, validate, or authorize artistic output.
        """
        if not 1 <= limit <= 4:
            raise ValueError("parallel provider limit must be from 1 to 4.")
        candidates = self.candidates(role)[:limit]
        if not candidates:
            raise ProviderUnavailable(f"No configured provider slot is eligible for role {role.upper()}.")
        if len(candidates) == 1:
            content, slot = self.complete(role=role, system=system, user=user)
            return ((content, slot),)

        results: dict[int, tuple[str, ProviderSlot]] = {}
        failures: dict[int, str] = {}
        with ThreadPoolExecutor(max_workers=len(candidates), thread_name_prefix="zen-provider") as executor:
            future_to_slot = {
                executor.submit(self.adapter.complete, slot, system=system, user=user): slot
                for slot in candidates
            }
            for future in as_completed(future_to_slot):
                slot = future_to_slot[future]
                try:
                    results[slot.number] = (future.result(), slot)
                except ProviderUnavailable as exc:
                    failures[slot.number] = str(exc)
                except Exception as exc:
                    # Adapter implementations are not allowed to tear down the
                    # router pool because one provider library misbehaved.
                    failures[slot.number] = f"{type(exc).__name__}"

        ordered = tuple(results[slot.number] for slot in candidates if slot.number in results)
        if ordered:
            return ordered
        detail = "; ".join(
            f"slot {slot.number}: {failures.get(slot.number, 'unavailable')}"
            for slot in candidates
        )
        raise ProviderUnavailable(detail or "No parallel provider completed the request.")
