from __future__ import annotations

import re

from ..models import Cue, Sequence


class SequenceProvider:
    """Read-only Sequence Pool inventory from MA2's List command."""

    command = "List Sequence"
    _line = re.compile(r"^\s*(?:sequence\s+)?(\d+)\s+['\"]?(.+?)['\"]?\s*$", re.I)

    def parse(self, output: str) -> list[Sequence]:
        sequences: list[Sequence] = []
        for line in output.splitlines():
            match = self._line.match(line.strip())
            if match:
                sequences.append(Sequence(int(match.group(1)), match.group(2).strip().strip("'\"")))
        return sequences


class CueProvider:
    """Read-only Cue metadata. Unknown feedback is ignored rather than guessed."""

    _line = re.compile(r"^\s*(?:cue\s+)?(\d+(?:\.\d+)?)\s+['\"]?(.+?)['\"]?(?:\s+(.*))?$", re.I)
    _trigger = re.compile(r"\btrigger\s*[:=]?\s*(.+?)(?=\s+(?:fade|delay)\b|$)", re.I)
    _timing = re.compile(r"\b(fade|delay)\s*[:=]?\s*(-?\d+(?:\.\d+)?)", re.I)

    @staticmethod
    def command(sequence: int) -> str:
        return f"List Cue {sequence}"

    def parse(self, output: str, sequence: int) -> list[Cue]:
        cues: list[Cue] = []
        for line in output.splitlines():
            match = self._line.match(line.strip())
            if not match:
                continue
            metadata = match.group(3) or ""
            trigger = self._trigger.search(metadata)
            values = {name.lower(): float(value) for name, value in self._timing.findall(metadata)}
            number = float(match.group(1))
            cues.append(Cue(sequence, int(number) if number.is_integer() else number, match.group(2).strip().strip("'\""), trigger.group(1).strip() if trigger else None, values.get("fade"), values.get("delay")))
        return cues
