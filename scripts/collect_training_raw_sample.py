"""Collect one completed multi-agent run as a RAW training candidate.

This script never approves, promotes, fine-tunes, or writes to MA2.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from zen_ma2_agent.training_dataset import write_raw_sample_from_completed_run


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect a review-first RAW ZEN training candidate.")
    parser.add_argument("run_path", type=Path)
    parser.add_argument("--destination-root", type=Path, default=Path.cwd())
    parser.add_argument("--request-file", type=Path)
    parser.add_argument("--show-context-ref", action="append", default=[])
    args = parser.parse_args()
    request_text = None
    if args.request_file:
        request_text = args.request_file.read_text(encoding="utf-8").strip()
    path = write_raw_sample_from_completed_run(
        args.run_path,
        args.destination_root,
        request_text=request_text,
        show_context_refs=args.show_context_ref,
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
