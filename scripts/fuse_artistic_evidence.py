"""Fuse retained reverse-translation and contextual evidence JSON offline."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from zen_ma2_agent.artistic_evidence_fusion import fuse_artistic_evidence


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sequence_reference", type=Path, help="Existing reverse-translation JSON")
    parser.add_argument("--context", type=Path, action="append", default=[], help="Read-only context evidence JSON; repeatable")
    parser.add_argument("--hypotheses", type=Path, help="Optional read-only hypothesis JSON")
    parser.add_argument("--output", type=Path, help="Write UTF-8 JSON to a new file; refuses to overwrite")
    args = parser.parse_args(argv)
    try:
        reference = _load_json(args.sequence_reference)
        context = [_load_json(path) for path in args.context]
        hypotheses = _load_json(args.hypotheses) if args.hypotheses else None
        if not isinstance(reference, dict) or not all(isinstance(item, dict) for item in context):
            raise ValueError("Evidence files must contain JSON objects.")
        if hypotheses is not None and not isinstance(hypotheses, dict):
            raise ValueError("Hypothesis file must contain a JSON object.")
        result = fuse_artistic_evidence(reference, context, hypotheses)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(2, f"Evidence fusion failed: {exc}\n")
    if args.output:
        try:
            with args.output.open("x", encoding="utf-8") as target:
                json.dump(result, target, indent=2, ensure_ascii=False)
                target.write("\n")
        except OSError as exc:
            parser.exit(2, f"Cannot write evidence fusion: {exc}\n")
    else:
        json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
