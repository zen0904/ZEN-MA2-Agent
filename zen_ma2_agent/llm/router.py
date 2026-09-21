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
import base64
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from time import monotonic
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..portable import portable_state_path


class ProviderUnavailable(RuntimeError):
    """A safe, key-free explanation that a slot could not serve a request."""

    def __init__(
        self,
        message: str,
        *,
        provider_attempts: Iterable[dict[str, object]] = (),
    ) -> None:
        super().__init__(message)
        # Runtime callers may preserve these bounded rows in their run
        # diagnostics.  They intentionally contain safe identities only.
        self.provider_attempts = tuple(provider_attempts)


@dataclass(frozen=True)
class ProviderImageInput:
    """Verified image bytes for one multimodal provider request.

    Deliberately contains no local path. Runtime code validates provenance and
    file location before constructing this transport-only value.
    """

    media_type: str
    image_bytes: bytes
    sha256: str

    MAX_BYTES = 10 * 1024 * 1024
    _SIGNATURES = {
        "image/png": lambda value: value.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/jpeg": lambda value: value.startswith(b"\xff\xd8\xff"),
        "image/webp": lambda value: len(value) >= 12 and value[:4] == b"RIFF" and value[8:12] == b"WEBP",
    }

    def __post_init__(self) -> None:
        if self.media_type not in self._SIGNATURES:
            raise ValueError("Provider image input MIME type is not supported.")
        if not isinstance(self.image_bytes, bytes) or not self.image_bytes or len(self.image_bytes) > self.MAX_BYTES:
            raise ValueError("Provider image input must be non-empty and no larger than 10 MiB.")
        if not self._SIGNATURES[self.media_type](self.image_bytes):
            raise ValueError("Provider image bytes do not match the declared MIME type.")
        digest = hashlib.sha256(self.image_bytes).hexdigest()
        if self.sha256 != digest:
            raise ValueError("Provider image input SHA-256 does not match its bytes.")


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
    reasoning_effort: str | None = None

    #: Provider types that are expected to run without any credential (a
    #: local OpenAI-compatible server such as Ollama or llama.cpp).  Cloud
    #: types still require a non-empty ``api_key`` so a missing credential
    #: fails loudly instead of silently marking the slot unconfigured.
    LOCAL_TYPES = frozenset({"OPENAI_COMPATIBLE_LOCAL"})
    COST_CLASSES = frozenset({"FREE", "LOCAL", "PAID", "UNKNOWN"})
    RESPONSE_FORMATS = frozenset({"JSON_OBJECT", "NONE"})
    REASONING_EFFORTS = frozenset({"LOW", "MEDIUM", "HIGH", "MAX"})

    def __post_init__(self) -> None:
        configured = (self.reasoning_effort or "").strip().upper()
        if configured and configured not in self.REASONING_EFFORTS:
            raise ValueError(
                f"Provider {self.number} reasoning effort must be LOW, MEDIUM, HIGH, or MAX."
            )
        object.__setattr__(self, "reasoning_effort", configured or None)

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
            "reasoning_effort": self.reasoning_effort,
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
            reasoning_effort=values.get(prefix + "REASONING_EFFORT", ""),
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

    def complete(
        self,
        slot: ProviderSlot,
        *,
        system: str,
        user: str,
        visual_evidence: ProviderImageInput | None = None,
    ) -> str:
        if slot.provider_type not in {"OPENAI_COMPATIBLE", "OPENAI", "OPENAI_COMPATIBLE_LOCAL"}:
            raise ProviderUnavailable(f"Provider slot {slot.number} type is not implemented: {slot.provider_type or 'UNSET'}")
        endpoint = slot.base_url.rstrip("/")
        if not endpoint.endswith("/chat/completions"):
            endpoint += "/chat/completions"
        user_content: str | list[dict[str, object]] = user
        if visual_evidence is not None:
            encoded_image = base64.b64encode(visual_evidence.image_bytes).decode("ascii")
            user_content = [
                {"type": "text", "text": user},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{visual_evidence.media_type};base64,{encoded_image}"
                    },
                },
            ]
        body_payload: dict[str, object] = {
            "model": slot.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user_content}],
            "temperature": 0.2,
        }
        if slot.response_format == "JSON_OBJECT":
            body_payload["response_format"] = {"type": "json_object"}
        if slot.reasoning_effort is not None:
            body_payload["reasoning_effort"] = slot.reasoning_effort.lower()
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

    def complete_with_image(
        self,
        slot: ProviderSlot,
        *,
        system: str,
        user: str,
        visual_evidence: ProviderImageInput,
    ) -> str:
        """Send text and verified image bytes in an OpenAI-compatible request."""
        return self.complete(
            slot,
            system=system,
            user=user,
            visual_evidence=visual_evidence,
        )


class ProviderRouter:
    def __init__(
        self,
        mode: str,
        slots: Iterable[ProviderSlot],
        adapter: OpenAICompatibleHTTPAdapter | None = None,
        *,
        parallelism: int = 1,
        parallel_roles: Iterable[str] = (),
    ):
        if not 1 <= parallelism <= 4:
            raise ValueError("parallelism must be from 1 to 4.")
        self.mode = mode
        self.slots = tuple(slots)
        self.adapter = adapter or OpenAICompatibleHTTPAdapter()
        self.parallelism = parallelism
        self.parallel_roles = frozenset(role.strip().upper() for role in parallel_roles if role.strip())

    @classmethod
    def from_portable_config(cls, path: Path | None = None) -> "ProviderRouter":
        mode, slots = load_provider_slots(path)
        values = _read_private_env(path)
        try:
            parallelism = int(values.get("ZEN_PROVIDER_PARALLELISM", "1"))
        except ValueError as exc:
            raise ValueError("ZEN_PROVIDER_PARALLELISM must be an integer.") from exc
        roles = tuple(
            role.strip().upper()
            for role in values.get("ZEN_PROVIDER_PARALLEL_ROLES", "").split(",")
            if role.strip()
        )
        return cls(mode, slots, parallelism=parallelism, parallel_roles=roles)

    def parallel_limit(self, role: str) -> int:
        normalized = role.upper()
        if self.parallelism <= 1:
            return 1
        if self.parallel_roles and normalized not in self.parallel_roles:
            return 1
        return min(self.parallelism, len(self.candidates(normalized)) or 1)

    def configured_slots(self) -> tuple[ProviderSlot, ...]:
        return tuple(slot for slot in self.slots if slot.configured)

    def pool_readiness(
        self,
        *,
        health_by_slot: dict[int, bool | str] | None = None,
        failure_by_slot: dict[int, str] | None = None,
        roles: Iterable[str] = ("RESEARCHER", "LIGHTING_DESIGNER", "CRITIC", "FINALIZER"),
    ) -> dict[str, object]:
        """Return a key-free, read-only provider-pool readiness projection.

        Health is deliberately UNKNOWN unless a caller supplies an external
        probe result; constructing this diagnostic never makes provider calls.
        """
        health_by_slot = health_by_slot or {}
        failure_by_slot = failure_by_slot or {}
        roles = tuple(str(role).upper() for role in roles)
        slot_rows: list[dict[str, object]] = []
        for slot in self.slots:
            configured = slot.configured
            health = health_by_slot.get(slot.number, "UNKNOWN") if configured else False
            if isinstance(health, str):
                health = health.upper()
            failure = failure_by_slot.get(slot.number)
            if failure is None:
                failure = "NOT_CONFIGURED" if not configured else ("NOT_TESTED" if health == "UNKNOWN" else "NONE")
            eligible_roles = [str(role).upper() for role in roles if slot.supports(str(role))]
            slot_rows.append({
                "identity": slot.safe_identity(),
                "configured": configured,
                "healthy": health,
                "eligible_roles": eligible_roles,
                "cost_class": slot.cost_class,
                "failure_class": failure,
            })

        role_rows: dict[str, dict[str, object]] = {}
        for role in roles:
            normalized = str(role).upper()
            eligible = self.candidates(normalized)
            required = self.parallelism if self.parallelism > 1 and normalized in self.parallel_roles else 1
            known_health = [health_by_slot.get(slot.number) for slot in eligible]
            healthy_count = sum(value is True or value == "ONLINE" for value in known_health)
            if not known_health:
                status = "NOT_READY"
            elif not health_by_slot or all(value in (None, "UNKNOWN") for value in known_health):
                status = "UNKNOWN"
            elif healthy_count >= required:
                status = "READY"
            else:
                status = "INSUFFICIENT_HEALTHY_PROVIDERS"
            role_rows[normalized] = {
                "configured_parallelism": required,
                "eligible_configured_slots": [slot.number for slot in eligible],
                "healthy_independent_slots": healthy_count,
                "parallelism_satisfied": healthy_count >= required if health_by_slot else "UNKNOWN",
                "status": status,
            }
        return {
            "schema": "zen.provider_pool_readiness.v0.1",
            "mode": self.mode,
            "parallelism": self.parallelism,
            "parallel_roles": sorted(self.parallel_roles),
            "slots": slot_rows,
            "roles": role_rows,
            "secrets_included": False,
        }

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

    def complete(
        self,
        *,
        role: str,
        system: str,
        user: str,
        visual_evidence: ProviderImageInput | None = None,
    ) -> tuple[str, ProviderSlot]:
        content, slot, _attempts = self.complete_with_diagnostics(
            role=role,
            system=system,
            user=user,
            visual_evidence=visual_evidence,
        )
        return content, slot

    def complete_with_diagnostics(
        self,
        *,
        role: str,
        system: str,
        user: str,
        visual_evidence: ProviderImageInput | None = None,
    ) -> tuple[str, ProviderSlot, tuple[dict[str, object], ...]]:
        """Run normal ordered fallback and return secret-free attempt evidence.

        This preserves ``complete`` routing semantics: candidates are tried in
        the same order, PRIMARY_ONLY still stops after its first candidate,
        and the first transport-successful response is returned unchanged.
        """
        candidates = self.candidates(role)
        if not candidates:
            raise ProviderUnavailable(f"No configured provider slot is eligible for role {role.upper()}.")
        failures: list[str] = []
        attempts: list[dict[str, object]] = []
        for attempt_order, slot in enumerate(candidates, start=1):
            started = monotonic()
            try:
                if visual_evidence is None:
                    content = self.adapter.complete(slot, system=system, user=user)
                else:
                    image_method = getattr(self.adapter, "complete_with_image", None)
                    if not callable(image_method):
                        raise ProviderUnavailable("Provider adapter does not support visual evidence input.")
                    content = image_method(
                        slot,
                        system=system,
                        user=user,
                        visual_evidence=visual_evidence,
                    )
            except ProviderUnavailable as exc:
                failures.append(f"slot {slot.number}: {exc}")
                failure_class, failure_reason = _parallel_failure_diagnostic(exc, None)
                attempts.append({
                    "slot_number": slot.number,
                    "provider_identity": slot.safe_identity(),
                    "attempt_order": attempt_order,
                    "transport_status": "FAILURE",
                    "failure_class": failure_class,
                    "failure_reason": failure_reason,
                    "provider_elapsed_seconds": round(monotonic() - started, 3),
                    "role_output_validation": "NOT_RUN",
                    "candidate_status": "TRANSPORT_FAILURE" if failure_class == "TRANSPORT_FAILURE" else "PROVIDER_ERROR",
                    "visual_evidence_sent": "YES" if visual_evidence is not None and callable(getattr(self.adapter, "complete_with_image", None)) else "NO",
                    "visual_evidence_sha256": visual_evidence.sha256 if visual_evidence is not None else None,
                })
                if self.mode == "PRIMARY_ONLY":
                    break
                continue
            attempts.append({
                "slot_number": slot.number,
                "provider_identity": slot.safe_identity(),
                "attempt_order": attempt_order,
                "transport_status": "SUCCESS",
                "failure_class": "NONE",
                "failure_reason": None,
                "provider_elapsed_seconds": round(monotonic() - started, 3),
                "role_output_validation": "NOT_RUN",
                "candidate_status": "TRANSPORT_SUCCESS",
                "visual_evidence_sent": "YES" if visual_evidence is not None else "NO",
                "visual_evidence_sha256": visual_evidence.sha256 if visual_evidence is not None else None,
            })
            return content, slot, tuple(attempts)
        raise ProviderUnavailable(
            "; ".join(failures) or "No eligible provider completed the request.",
            provider_attempts=attempts,
        )

    def complete_parallel(
        self,
        *,
        role: str,
        system: str,
        user: str,
        limit: int = 2,
    ) -> tuple[tuple[str, ProviderSlot], ...]:
        """Return up to ``limit`` transport successes in preference order."""
        results, attempts = self.complete_parallel_with_diagnostics(
            role=role,
            system=system,
            user=user,
            limit=limit,
        )
        if not results:
            failures = [
                f"slot {item['slot_number']}: {item['failure_reason']}"
                for item in attempts
                if item["transport_status"] == "FAILURE"
            ]
            raise ProviderUnavailable("; ".join(failures) or "No eligible provider completed the request.")
        return results

    def complete_parallel_with_diagnostics(
        self,
        *,
        role: str,
        system: str,
        user: str,
        limit: int = 2,
    ) -> tuple[tuple[tuple[str, ProviderSlot], ...], tuple[dict[str, object], ...]]:
        """Collect bounded transport successes and key-free per-provider outcomes.

        ``limit`` is the desired number of successful provider responses, not
        the size of the first slice of the eligible pool. Attempts preserve
        router preference order, backfill later candidates after failures, and
        never call a candidate more than once in this stage. Each batch is
        bounded by configured ``parallelism``. Returned completions and
        diagnostics are deterministic even when requests finish out of order.
        """
        if not 1 <= limit <= 4:
            raise ValueError("parallel provider limit must be from 1 to 4.")
        candidates = self.candidates(role)
        if not candidates:
            raise ProviderUnavailable(f"No configured provider slot is eligible for role {role.upper()}.")
        desired_successes = min(limit, len(candidates))
        concurrency = min(self.parallelism, desired_successes)
        results: dict[int, tuple[str, ProviderSlot]] = {}
        diagnostics: dict[int, dict[str, object]] = {}
        next_index = 0
        attempt_order = 0

        def invoke(slot: ProviderSlot) -> tuple[str | None, float, Exception | None]:
            started = monotonic()
            try:
                return self.adapter.complete(slot, system=system, user=user), monotonic() - started, None
            except Exception as exc:  # isolate provider and adapter failures
                return None, monotonic() - started, exc

        while len(results) < desired_successes and next_index < len(candidates):
            remaining = desired_successes - len(results)
            batch = candidates[next_index: next_index + min(concurrency, remaining)]
            indexed_batch: list[tuple[int, ProviderSlot]] = []
            for slot in batch:
                attempt_order += 1
                indexed_batch.append((attempt_order, slot))
            next_index += len(batch)

            with ThreadPoolExecutor(max_workers=len(batch), thread_name_prefix="zen-provider") as executor:
                future_to_attempt = {
                    executor.submit(invoke, slot): (order, slot)
                    for order, slot in indexed_batch
                }
                completed: dict[int, tuple[str | None, float, Exception | None]] = {}
                for future in as_completed(future_to_attempt):
                    order, _slot = future_to_attempt[future]
                    try:
                        completed[order] = future.result()
                    except Exception as exc:  # defensive: invoke normally captures this
                        completed[order] = (None, 0.0, exc)

            for order, slot in indexed_batch:
                content, elapsed, error = completed[order]
                if error is None and isinstance(content, str) and content.strip():
                    results[slot.number] = (content, slot)
                    diagnostics[slot.number] = {
                        "slot_number": slot.number,
                        "provider_identity": slot.safe_identity(),
                        "attempt_order": order,
                        "transport_status": "SUCCESS",
                        "failure_class": "NONE",
                        "failure_reason": None,
                        "provider_elapsed_seconds": round(elapsed, 3),
                    }
                else:
                    failure_class, failure_reason = _parallel_failure_diagnostic(error, content)
                    diagnostics[slot.number] = {
                        "slot_number": slot.number,
                        "provider_identity": slot.safe_identity(),
                        "attempt_order": order,
                        "transport_status": "FAILURE",
                        "failure_class": failure_class,
                        "failure_reason": failure_reason,
                        "provider_elapsed_seconds": round(elapsed, 3),
                    }

        ordered_results = tuple(results[slot.number] for slot in candidates if slot.number in results)
        ordered_diagnostics = tuple(
            sorted(diagnostics.values(), key=lambda row: int(row["attempt_order"]))
        )
        return ordered_results, ordered_diagnostics


def _parallel_failure_diagnostic(error: Exception | None, content: str | None) -> tuple[str, str]:
    """Classify a failed call without persisting provider error text or secrets."""
    if error is None:
        return "PROVIDER_ERROR", "EMPTY_PROVIDER_RESPONSE"
    if isinstance(error, ProviderUnavailable):
        message = str(error).casefold()
        http_match = re.search(r"httperror\s+(\d{3})", message)
        if http_match:
            return "TRANSPORT_FAILURE", f"HTTPError {http_match.group(1)}"
        if any(marker in message for marker in ("timeout", "timed out", "socket.timeout")):
            return "TRANSPORT_FAILURE", "TIMEOUT"
        if any(marker in message for marker in ("urlerror", "connectionerror", "connection refused", "connection failed")):
            return "TRANSPORT_FAILURE", "CONNECTION_ERROR"
        if "no chat completion content" in message:
            return "PROVIDER_ERROR", "NO_CHAT_COMPLETION_CONTENT"
        if "empty chat completion content" in message:
            return "PROVIDER_ERROR", "EMPTY_CHAT_COMPLETION"
        return "PROVIDER_ERROR", "PROVIDER_UNAVAILABLE"
    # Never serialize arbitrary exception text; it can contain request details.
    return "PROVIDER_ERROR", type(error).__name__[:80]
