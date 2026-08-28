from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

from .models import SafetyLevel
from .skill_system import SkillError, SkillManifest


@dataclass(frozen=True)
class SkillProposal:
    id: str
    name: str
    intent: str
    required_state: tuple[str, ...]
    safety: str
    files: tuple[str, ...]
    status: str = "PENDING_APPROVAL"

    def summary(self) -> dict:
        return asdict(self)


class ExtensionManager:
    """Creates only installed skill stubs after an explicit core approval."""

    def __init__(self, root: Path):
        self.root = root
        self.proposals: dict[str, SkillProposal] = {}

    def propose(self, name: str, intent: str, required_state: list[str], safety: str) -> SkillProposal:
        if not re.fullmatch(r"[a-z][a-z0-9_]*", intent):
            raise SkillError("Proposed intent must be lowercase snake_case.")
        if safety not in {item.value for item in SafetyLevel}:
            raise SkillError("Proposed safety is invalid.")
        slug = intent.replace("_", ".")
        proposal = SkillProposal(uuid.uuid4().hex[:12], name, intent, tuple(required_state), safety, (f"skills/installed/{slug}/manifest.json", f"skills/installed/{slug}/skill.py"))
        self.proposals[proposal.id] = proposal
        return proposal

    def install(self, proposal_id: str) -> SkillProposal:
        proposal = self.proposals.get(proposal_id)
        if not proposal or proposal.status != "PENDING_APPROVAL":
            raise SkillError("Proposal is not awaiting approval.")
        skill_id = proposal.intent.replace("_", ".")
        target = self.root / "skills" / "installed" / skill_id
        if target.exists():
            raise SkillError("A skill with this id is already installed.")
        target.mkdir(parents=True)
        manifest = {"id": skill_id, "name": proposal.name, "version": "0.1", "description": "User-installed proposal stub; implementation review required.", "intents": [proposal.intent], "required_state": list(proposal.required_state), "safety": proposal.safety, "enabled": False}
        SkillManifest.from_dict(manifest, "installed", enabled=False)
        (target / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (target / "skill.py").write_text("# Deliberately not imported by ZEN. Complete via reviewed declarative Skill API.\n", encoding="utf-8")
        installed = SkillProposal(**{**asdict(proposal), "status": "INSTALLED"})
        self.proposals[proposal_id] = installed
        return installed
