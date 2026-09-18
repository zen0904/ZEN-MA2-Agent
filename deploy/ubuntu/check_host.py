"""Compatibility wrapper for the canonical cross-platform host preflight."""

from __future__ import annotations

from scripts.host_preflight import main


if __name__ == "__main__":
    raise SystemExit(main())
