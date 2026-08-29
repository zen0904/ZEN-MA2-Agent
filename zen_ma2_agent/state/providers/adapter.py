from __future__ import annotations

import re
import secrets
from dataclasses import dataclass
from typing import Any


class AdapterResponseError(ValueError):
    pass


class AdapterUnsupported(AdapterResponseError):
    pass


@dataclass(frozen=True)
class AdapterRequest:
    request_id: str
    command: str
    argument: int | None = None

    @property
    def wire(self) -> str:
        return f"{self.request_id}|{self.command}" + (f"|{self.argument}" if self.argument is not None else "")


class ZenStateAdapter:
    """Compiler/parser for the read-only ZEN_AGENT UserVar mailbox protocol."""

    source = "ma2_lua_adapter"
    _request_id = re.compile(r"^[A-Za-z0-9_-]{6,64}$")
    _commands = frozenset({"groups", "fixtures", "group_membership", "layouts", "layout_items", "sequences", "cues", "selection", "programmer"})
    _requires_number = frozenset({"group_membership", "layouts", "layout_items", "cues"})
    _frame = re.compile(r"ZEN_STATE\|(?P<request_id>[A-Za-z0-9_-]+)\|(?P<kind>BEGIN|MEMBER|END|ERROR)(?:\|(?P<payload>[^\r\n]*))?")

    @classmethod
    def request(cls, command: str, argument: int | None = None, *, request_id: str | None = None) -> AdapterRequest:
        if command not in cls._commands:
            raise ValueError("Unknown ZEN_AGENT read-only command.")
        if command in cls._requires_number:
            if isinstance(argument, bool) or not isinstance(argument, int) or argument < 1:
                raise ValueError(f"ZEN_AGENT {command} requires a positive numeric argument.")
        elif argument is not None:
            raise ValueError(f"ZEN_AGENT {command} does not accept an argument.")
        request_id = request_id or secrets.token_hex(8)
        if not cls._request_id.fullmatch(request_id):
            raise ValueError("Invalid ZEN_AGENT request id.")
        return AdapterRequest(request_id, command, argument)

    @staticmethod
    def plugin_slot(settings: object) -> int:
        settings = settings if isinstance(settings, dict) else {}
        slot = settings.get("plugin_slot")
        if isinstance(slot, bool) or not isinstance(slot, int) or not 2 <= slot <= 9999:
            raise AdapterUnsupported("UNSUPPORTED ZEN_AGENT: configure state_adapter.plugin_slot with the imported Plugin Pool slot.")
        return slot

    @staticmethod
    def timeout_seconds(settings: object) -> float:
        settings = settings if isinstance(settings, dict) else {}
        try:
            timeout = float(settings.get("timeout_seconds", 3.0))
        except (TypeError, ValueError) as exc:
            raise ValueError("ZEN_AGENT timeout must be numeric.") from exc
        if not 0.1 <= timeout <= 30:
            raise ValueError("ZEN_AGENT timeout must be from 0.1 to 30 seconds.")
        return timeout

    def _frames(self, output: str, request: AdapterRequest) -> list[tuple[str, str]]:
        frames = [(match.group("kind"), match.group("payload") or "") for match in self._frame.finditer(output) if match.group("request_id") == request.request_id]
        if not frames:
            raise AdapterResponseError(f"No ZEN_STATE response matching request id {request.request_id}.")
        for kind, payload in frames:
            if kind == "ERROR":
                raise AdapterUnsupported(f"UNSUPPORTED {request.command}: {payload or 'adapter reported an error'}")
        return frames

    def group_membership(self, output: str, request: AdapterRequest) -> dict[str, Any]:
        if request.command != "group_membership" or request.argument is None:
            raise ValueError("Group membership parser requires a group_membership mailbox request.")
        frames = self._frames(output, request)
        expected = f"group_membership|{request.argument}"
        if frames[0] != ("BEGIN", expected) or frames[-1] != ("END", expected):
            raise AdapterResponseError("Malformed group membership response framing.")
        fixtures: list[int] = []
        for kind, payload in frames[1:-1]:
            if kind != "MEMBER" or not re.fullmatch(r"[1-9]\d*", payload):
                raise AdapterResponseError("Malformed group membership fixture ID.")
            fixtures.append(int(payload))
        return {"group_no": request.argument, "fixtures": fixtures}

    def unsupported_resource(self, output: str, request: AdapterRequest) -> None:
        """Keep the dispatcher generic while this Lua revision implements membership only."""
        self._frames(output, request)
        raise AdapterUnsupported(f"UNSUPPORTED {request.command}: no safe mailbox parser is implemented yet.")
