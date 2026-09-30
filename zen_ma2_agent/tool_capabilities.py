"""Shared agent-facing tool capability registry.

The registry describes what ZEN can reason about and how a capability may be
reached. It is intentionally not an execution router. In particular, exposing a
capability to a model never grants shell, MCP, Telnet, Lua, or MA write
authority.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

REGISTRY_SCHEMA = "zen.agent_tool_capabilities.v0.1"
CONTEXT_SCHEMA = "zen.agent_tool_context.v0.1"


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_agent_tool_registry(repo_root: Path | None = None) -> dict[str, Any]:
    root = Path(repo_root) if repo_root is not None else _default_repo_root()
    path = root / "data" / "zen_agent_tool_capabilities.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema") != REGISTRY_SCHEMA:
        raise ValueError(f"Invalid agent tool registry schema at {path}.")
    if not isinstance(value.get("capabilities"), list):
        raise ValueError(f"Agent tool registry capabilities must be a list at {path}.")
    return value


def build_agent_tool_context(
    repo_root: Path | None = None,
    *,
    classes: Iterable[str] | None = None,
) -> dict[str, Any]:
    registry = load_agent_tool_registry(repo_root)
    wanted = None if classes is None else {str(item).strip().upper() for item in classes}
    capabilities: list[dict[str, Any]] = []
    for item in registry["capabilities"]:
        if not isinstance(item, dict):
            continue
        item_class = str(item.get("class") or "").upper()
        if wanted is not None and item_class not in wanted:
            continue
        capabilities.append(
            {
                key: item[key]
                for key in (
                    "id",
                    "title",
                    "status",
                    "class",
                    "invoke_via",
                    "interactive_chatgpt",
                    "lean_api_designer_direct",
                    "uses",
                    "limits",
                )
                if key in item
            }
        )
    capabilities.sort(key=lambda item: str(item.get("id") or ""))
    return {
        "schema": CONTEXT_SCHEMA,
        "execution_note": (
            "Capability visibility is not execution authority. The ordinary Lean API Designer "
            "currently receives no direct tools; runtime adapters/brokers must acquire evidence "
            "outside the model call. MA writes remain behind Compiler, Preview, human Approval, "
            "deterministic Builder, and native readback."
        ),
        "capabilities": capabilities,
    }


__all__ = [
    "REGISTRY_SCHEMA",
    "CONTEXT_SCHEMA",
    "load_agent_tool_registry",
    "build_agent_tool_context",
]
