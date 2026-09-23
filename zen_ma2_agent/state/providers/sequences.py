from __future__ import annotations

import re

from ..models import Cue, Sequence


class SequenceProvider:
    """Read-only Sequence Pool inventory from MA2's List command."""

    command = "List Sequence"
    _line = re.compile(r"^\s*(?:sequence\s+)?(\d+)\s+['\"]?(.+?)['\"]?\s*$", re.I)
    # Verified grandMA2 3.9 table row, for example:
    # ``Sequ 201 201  ZEN_AI_TEST_SONG  On ...``.  The first two columns
    # both represent the Sequence number; retain the explicit pool column
    # instead of treating the row as an arbitrary display string.
    _table = re.compile(r"^\s*sequ(?:ence)?\s+(\d+)\s+(\d+)\s+(.+?)\s+(?:on|off)\b", re.I)

    def parse(self, output: str) -> list[Sequence]:
        sequences: list[Sequence] = []
        for line in output.splitlines():
            table = self._table.match(line.strip())
            if table:
                displayed, number, name = table.groups()
                if displayed == number:
                    sequences.append(Sequence(int(number), name.strip().strip("'\"")))
                continue
            match = self._line.match(line.strip())
            if match:
                sequences.append(Sequence(int(match.group(1)), match.group(2).strip().strip("'\"")))
        return sequences


class CueProvider:
    """Read-only Cue metadata. Unknown feedback is ignored rather than guessed."""

    _line = re.compile(r"^\s*(?:cue\s+)?(\d+(?:\.\d+)?)\s+['\"]?(.+?)['\"]?(?:\s+(.*))?$", re.I)
    _trigger = re.compile(r"\btrigger\s*[:=]?\s*(.+?)(?=\s+(?:fade|delay)\b|$)", re.I)
    _timing = re.compile(r"\b(fade|delay)\s*[:=]?\s*(-?\d+(?:\.\d+)?)", re.I)
    # Verified grandMA2 3.9 Detail List row. The first `0` is Part 0, not
    # the Cue number; callers pass their explicit queried Cue number.
    _detail = re.compile(r"^\s*cue\s+0\s+(.+?)\s{2,}(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\b", re.I)

    @staticmethod
    def command(sequence: int) -> str:
        return f"List Cue {sequence}"

    @staticmethod
    def detail_command(sequence: int, cue_number: int) -> str:
        if not isinstance(sequence, int) or not isinstance(cue_number, int) or sequence < 1 or cue_number < 1:
            raise ValueError("Cue detail requires positive Sequence and Cue numbers.")
        return f"List Cue {cue_number} Part 0 Sequence {sequence}"

    def parse_detail(self, output: str, sequence: int, cue_number: int) -> Cue | None:
        """Parse MA2's detailed Part-0 feedback for one explicitly addressed Cue."""
        for line in output.splitlines():
            match = self._detail.match(line.strip())
            if match:
                name, delay, fade = match.groups()
                return Cue(sequence, cue_number, name.strip().strip("'\""), None, float(fade), float(delay))
        return None

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
