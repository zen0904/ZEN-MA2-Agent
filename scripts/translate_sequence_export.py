"""Translate a retained native MA2 Sequence XML file without contacting MA2."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from zen_ma2_agent.reverse_artistic_translator import translate_sequence_xml


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xml", type=Path, help="Existing native Export Sequence XML file")
    parser.add_argument("--sequence", type=int, required=True, help="Sequence number exported from MA2")
    parser.add_argument("--output", type=Path, help="Write UTF-8 JSON to a new file; refuses to overwrite")
    args = parser.parse_args(argv)
    try:
        result = translate_sequence_xml(args.xml.read_bytes(), args.sequence)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Sequence translation failed: {exc}\n")
    if args.output:
        try:
            with args.output.open("x", encoding="utf-8") as target:
                json.dump(result, target, indent=2, ensure_ascii=False)
                target.write("\n")
        except OSError as exc:
            parser.exit(2, f"Cannot write design reference: {exc}\n")
    else:
        json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
