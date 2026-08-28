from __future__ import annotations

import re

from .models import CommandPlan, Intent, SafetyLevel


DANGEROUS = re.compile(r"\b(delete|patch|setup|psr|clearall)\b", re.I)
MODIFY = re.compile(r"\b(store|update|assign|clone|at)\b", re.I)


def classify(command: str) -> SafetyLevel:
    if DANGEROUS.search(command):
        return SafetyLevel.DANGEROUS
    if MODIFY.search(command):
        return SafetyLevel.MODIFY
    return SafetyLevel.SAFE


def build_plan(intent: Intent, preferences: dict) -> CommandPlan:
    kind, p = intent.kind, intent.parameters
    if kind == "select_group":
        command = f'Group "{p["group"]}"'
    elif kind == "beam_intensity":
        command = f'Group "{p["group"]}"; At {p["level"]}'
    elif kind == "go_sequence":
        command = f"Go Sequence {p['sequence']}"
    elif kind == "select_fixture_range":
        command = f"Fixture {p['first']} Thru {p['last']}"
    elif kind == "blackout":
        command = preferences.get("blackout_command_template")
        if not command:
            return CommandPlan(intent, None, SafetyLevel.DANGEROUS,
                               "Blackout is intentionally unconfigured. Set the show-approved blackout_command_template first.", False)
    else:
        raise ValueError(f"No command builder for intent: {kind}")
    level = classify(str(command))
    note = "Preview required before execution."
    if level is SafetyLevel.DANGEROUS:
        note = "Dangerous operation: a second confirmation is required."
    return CommandPlan(intent, str(command), level, note, True)
