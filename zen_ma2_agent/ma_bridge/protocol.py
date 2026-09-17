from __future__ import annotations

import hashlib
import json
import re
from collections import OrderedDict
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Mapping, Optional

PROTOCOL_VERSION = "ZEN/1"
MAX_LINE_BYTES = 1024
MAX_REQUEST_ID_LENGTH = 64
MAX_DESIGN_REQUEST_LENGTH = 128
DEFAULT_DEDUP_CAPACITY = 256

_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")
_DESIGN_REQUEST_RE = re.compile(r"^[A-Za-z0-9._:-]+$")
_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


class BridgeCommand(str, Enum):
    PING = "PING"
    STATUS = "STATUS"
    DIMMER = "DIMMER"
    DESIGN = "DESIGN"


class BridgeProtocolError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class BridgeRequest:
    protocol_version: str
    request_id: str
    command: BridgeCommand
    arguments: Mapping[str, Any]
    payload_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "protocol_version": self.protocol_version,
            "request_id": self.request_id,
            "command": self.command.value,
            "arguments": dict(self.arguments),
            "payload_hash": self.payload_hash,
        }


def _error(code: str, message: str) -> BridgeProtocolError:
    return BridgeProtocolError(code, message)


def _canonical_hash(
    request_id: str,
    command: BridgeCommand,
    arguments: Mapping[str, Any],
) -> str:
    payload = {
        "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id,
        "command": command.value,
        "arguments": dict(arguments),
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_request_id(request_id: str) -> str:
    if not request_id or len(request_id) > MAX_REQUEST_ID_LENGTH:
        raise _error("INVALID_REQUEST_ID", "request_id length is invalid")
    if not _REQUEST_ID_RE.fullmatch(request_id):
        raise _error("INVALID_REQUEST_ID", "request_id contains unsupported characters")
    return request_id


def _parse_argument_tokens(tokens: list[str]) -> Dict[str, str]:
    parsed: Dict[str, str] = {}
    for token in tokens:
        if "=" not in token:
            raise _error("INVALID_ARGUMENT", "arguments must use KEY=VALUE syntax")
        key, value = token.split("=", 1)
        if not _KEY_RE.fullmatch(key):
            raise _error("INVALID_ARGUMENT", "argument key is invalid")
        if not value:
            raise _error("INVALID_ARGUMENT", f"{key} value is empty")
        if key in parsed:
            raise _error("DUPLICATE_ARGUMENT", f"duplicate argument: {key}")
        parsed[key] = value
    return parsed


def _require_exact_arguments(
    raw: Mapping[str, str],
    *,
    required: set[str],
) -> None:
    missing = required - set(raw)
    if missing:
        raise _error("MISSING_ARGUMENT", f"missing argument: {sorted(missing)[0]}")
    unknown = set(raw) - required
    if unknown:
        raise _error("INVALID_ARGUMENT", f"unsupported argument: {sorted(unknown)[0]}")


def _parse_dimmer(raw: Mapping[str, str]) -> Dict[str, Any]:
    _require_exact_arguments(raw, required={"GROUP", "VALUE"})
    try:
        group = int(raw["GROUP"], 10)
    except ValueError as exc:
        raise _error("INVALID_ARGUMENT", "GROUP must be a positive integer") from exc
    if group <= 0:
        raise _error("INVALID_ARGUMENT", "GROUP must be a positive integer")

    try:
        value_number = float(raw["VALUE"])
    except ValueError as exc:
        raise _error("INVALID_ARGUMENT", "VALUE must be a number") from exc
    if not 0.0 <= value_number <= 100.0:
        raise _error("INVALID_ARGUMENT", "VALUE must be in range 0..100")
    value: int | float = (
        int(value_number) if value_number.is_integer() else value_number
    )
    return {"GROUP": group, "VALUE": value}


def _parse_design(raw: Mapping[str, str]) -> Dict[str, Any]:
    _require_exact_arguments(raw, required={"REQUEST"})
    request = raw["REQUEST"]
    if len(request) > MAX_DESIGN_REQUEST_LENGTH:
        raise _error("INVALID_ARGUMENT", "REQUEST exceeds maximum length")
    if not _DESIGN_REQUEST_RE.fullmatch(request):
        raise _error("INVALID_ARGUMENT", "REQUEST contains unsupported characters")
    return {"REQUEST": request}


def parse_request_line(line: str) -> BridgeRequest:
    if not isinstance(line, str) or not line:
        raise _error("INVALID_PROTOCOL", "request line must be non-empty text")
    if len(line.encode("utf-8")) > MAX_LINE_BYTES:
        raise _error("LINE_TOO_LONG", "request line exceeds maximum size")
    if any(ord(char) < 32 or ord(char) == 127 for char in line):
        raise _error("CONTROL_CHARACTER", "control characters are not accepted")

    tokens = line.split()
    if len(tokens) < 4:
        raise _error("INVALID_PROTOCOL", "request line is incomplete")
    if tokens[0] != PROTOCOL_VERSION:
        raise _error("INVALID_PROTOCOL", "unsupported protocol version")
    if tokens[1] != "REQ":
        raise _error("INVALID_PROTOCOL", "expected REQ message type")

    request_id = _validate_request_id(tokens[2])
    try:
        command = BridgeCommand(tokens[3])
    except ValueError as exc:
        raise _error("UNKNOWN_COMMAND", "unsupported command") from exc

    raw_arguments = _parse_argument_tokens(tokens[4:])
    if command in {BridgeCommand.PING, BridgeCommand.STATUS}:
        if raw_arguments:
            raise _error("INVALID_ARGUMENT", f"{command.value} accepts no arguments")
        arguments: Dict[str, Any] = {}
    elif command == BridgeCommand.DIMMER:
        arguments = _parse_dimmer(raw_arguments)
    elif command == BridgeCommand.DESIGN:
        arguments = _parse_design(raw_arguments)
    else:  # pragma: no cover
        raise _error("UNKNOWN_COMMAND", "unsupported command")

    return BridgeRequest(
        protocol_version=PROTOCOL_VERSION,
        request_id=request_id,
        command=command,
        arguments=arguments,
        payload_hash=_canonical_hash(request_id, command, arguments),
    )


def format_ready(request_id: str, payload: Optional[str] = None) -> str:
    request_id = _validate_request_id(request_id)
    if payload is None or payload == "":
        return f"{PROTOCOL_VERSION} READY {request_id}"
    if any(ord(char) < 32 or ord(char) == 127 for char in payload):
        raise ValueError("response payload contains control characters")
    if len(payload.encode("utf-8")) > MAX_LINE_BYTES:
        raise ValueError("response payload exceeds maximum size")
    return f"{PROTOCOL_VERSION} READY {request_id} {payload}"


def format_error(request_id: str, error_code: str) -> str:
    request_id = _validate_request_id(request_id)
    if not _KEY_RE.fullmatch(error_code):
        raise ValueError("error_code is invalid")
    return f"{PROTOCOL_VERSION} ERROR {request_id} {error_code}"


class RequestDeduplicator:
    """Bounded request-id cache. It never executes or dispatches requests."""

    def __init__(self, capacity: int = DEFAULT_DEDUP_CAPACITY):
        if not isinstance(capacity, int) or capacity < 1:
            raise ValueError("dedup capacity must be a positive integer")
        self.capacity = capacity
        self._seen: OrderedDict[str, str] = OrderedDict()

    def check(self, request: BridgeRequest) -> str:
        previous = self._seen.get(request.request_id)
        if previous is not None:
            self._seen.move_to_end(request.request_id)
            if previous == request.payload_hash:
                return "DUPLICATE"
            raise _error(
                "REQUEST_ID_CONFLICT",
                "request_id was already used for a different payload",
            )

        self._seen[request.request_id] = request.payload_hash
        self._seen.move_to_end(request.request_id)
        while len(self._seen) > self.capacity:
            self._seen.popitem(last=False)
        return "NEW"

    def __len__(self) -> int:
        return len(self._seen)
