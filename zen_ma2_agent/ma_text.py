"""Fail-closed ASCII validation for text crossing the grandMA2 boundary."""
from __future__ import annotations

from typing import Any


class NonAsciiMATextError(ValueError):
    """Raised when MA-bound text contains a non-ASCII character."""


def validate_ma_text(value: str, *, field: str = "text") -> str:
    """Validate one MA-bound name, label, command, Macro, or Plugin body."""
    if not isinstance(value, str):
        raise NonAsciiMATextError(f"NON_ASCII_MA_TEXT: {field} must be text.")
    for index, character in enumerate(value):
        if ord(character) > 0x7F:
            raise NonAsciiMATextError(
                f"NON_ASCII_MA_TEXT: {field} contains U+{ord(character):04X} at index {index}."
            )
    return value


def validate_ma_payload(value: Any, *, path: str = "root") -> Any:
    """Validate every string in an MA-bound structured payload.

    This deliberately does not strip or transliterate.  Failing closed before
    Builder/transport integration is safer than silently changing operator text.
    """
    if isinstance(value, str):
        return validate_ma_text(value, field=path)
    if isinstance(value, dict):
        for key, child in value.items():
            validate_ma_text(str(key), field=f"{path}.key")
            validate_ma_payload(child, path=f"{path}.{key}")
        return value
    if isinstance(value, list):
        for index, child in enumerate(value):
            validate_ma_payload(child, path=f"{path}[{index}]")
        return value
    if isinstance(value, tuple):
        for index, child in enumerate(value):
            validate_ma_payload(child, path=f"{path}[{index}]")
        return value
    return value


__all__ = ["NonAsciiMATextError", "validate_ma_text", "validate_ma_payload"]
